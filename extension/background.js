/**
 * MV3 service worker: the only place that talks to the backend (CAP-02).
 *
 * Why the fetch lives here and not in popup.js: under Manifest V3 a request
 * made by the service worker under a granted `host_permissions` entry is not
 * subject to page CORS, so the backend needs no CORS cooperation for the
 * extension to work. It also means the request survives the popup closing --
 * a popup's JS context is destroyed the moment the popup loses focus, which
 * would abort an in-flight fetch started there.
 *
 * COLD START (Phase 4 success criterion 2): an MV3 service worker is torn
 * down after ~30s idle and respawned to handle the next event. Two rules keep
 * that working, and both are load-bearing:
 *
 *   1. The onMessage listener is registered SYNCHRONOUSLY at the top level of
 *      this file. A listener registered after an `await`, or inside another
 *      callback, is not attached when the worker respawns to deliver the very
 *      event that woke it -- the message is silently dropped and the popup
 *      hangs forever. This is the single most common MV3 cold-start bug.
 *   2. No module-scope mutable state is relied on between messages. Anything
 *      cached up here is gone after a teardown, so every request carries what
 *      it needs.
 */

const BACKEND_ORIGIN = "http://localhost:8000";
// Two capture routes, deliberately separate endpoints:
//   /capture/text        — deterministic regex extraction (TRI-01). The demo
//                          and the DEMO-02 determinism tests run through here.
//   /capture/screenshots — vision extraction, not deterministic, so it is kept
//                          off the fixture path on purpose.
const TEXT_ENDPOINT = `${BACKEND_ORIGIN}/capture/text`;
const SCREENSHOTS_ENDPOINT = `${BACKEND_ORIGIN}/capture/screenshots`;

// Triage runs a real Bedrock call, so the ceiling is generous. It exists at
// all so a backend that never answers surfaces as a readable timeout in the
// popup rather than an indefinite spinner.
const REQUEST_TIMEOUT_MS = 120_000;

/**
 * POST the pasted job to /capture and return a plain result envelope.
 * Never throws: the popup renders `ok: false` as an error card.
 */
async function captureJob(endpoint, payload) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const bodyText = await response.text();

    if (!response.ok) {
      // FastAPI puts the useful part in {detail}; a bare status code tells the
      // user nothing actionable ("we couldn't read a title in those shots" is
      // the message that matters, not "422").
      let detail = bodyText.slice(0, 500);
      try {
        const parsed = JSON.parse(bodyText);
        if (parsed && parsed.detail) detail = String(parsed.detail);
      } catch {
        /* keep the raw body */
      }
      return {
        ok: false,
        error: `The backend returned ${response.status} ${response.statusText}.`,
        detail,
      };
    }

    try {
      return { ok: true, data: JSON.parse(bodyText) };
    } catch {
      return {
        ok: false,
        error: "The backend replied with something that is not JSON.",
        detail: bodyText.slice(0, 500),
      };
    }
  } catch (e) {
    if (e.name === "AbortError") {
      return {
        ok: false,
        error: `No reply within ${REQUEST_TIMEOUT_MS / 1000}s. The agent may still be running.`,
      };
    }
    // A failed fetch to localhost is nearly always "server not running".
    return {
      ok: false,
      error: `Could not reach the backend at ${BACKEND_ORIGIN}.`,
      detail: "Start it with: cd backend && uvicorn api:app --reload",
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

const ROUTES = {
  CAPTURE_JOB: TEXT_ENDPOINT,
  CAPTURE_SCREENSHOTS: SCREENSHOTS_ENDPOINT,
};

// Registered at top level -- see COLD START above. Returning true keeps the
// message channel open for the async sendResponse.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const endpoint = message && ROUTES[message.type];
  if (!endpoint) {
    return false;
  }

  captureJob(endpoint, message.payload).then(sendResponse);
  return true;
});
