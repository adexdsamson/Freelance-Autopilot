/**
 * Popup controller (CAP-01, CAP-03).
 *
 * Capture is paste-only by construction: the single source of job text is the
 * textarea below. Nothing here reads the active tab, injects a content script,
 * or touches the DOM of any page, and the optional URL field is provenance
 * metadata that is never fetched by the popup or the backend. That is the
 * Upwork-ToS constraint from PROJECT.md, kept structural rather than
 * conventional -- the extension requests no `tabs`, `activeTab` or
 * `scripting` permission in manifest.json, so scraping is not merely avoided,
 * it is unavailable.
 *
 * The fetch itself is delegated to the service worker (see background.js) --
 * a popup's JS context dies the instant the popup closes, which would abort
 * an in-flight request started here.
 */

const form = document.getElementById("capture-form");
const jobTextInput = document.getElementById("job-text");
const sourceUrlInput = document.getElementById("source-url");
const submitButton = document.getElementById("submit-button");
const screenshotButton = document.getElementById("screenshot-button");

const pendingPanel = document.getElementById("pending");
const errorPanel = document.getElementById("error");
const errorMessage = document.getElementById("error-message");
const errorDetail = document.getElementById("error-detail");
const retryButton = document.getElementById("retry-button");

const resultPanel = document.getElementById("result");
const verdictBadge = document.getElementById("verdict-badge");
const scoreEl = document.getElementById("score");
const reasoningEl = document.getElementById("reasoning");
const extractedEl = document.getElementById("extracted");
const newCaptureButton = document.getElementById("new-capture-button");

/**
 * Draft persistence (CAP-03 usability).
 *
 * An MV3 popup's document is torn down the instant the popup loses focus --
 * switching to another window to copy the posting's URL is enough to wipe a
 * half-pasted job. localStorage on the extension origin survives that teardown
 * and, unlike chrome.storage, needs NO manifest permission -- which matters
 * here because the extension deliberately declares an empty `permissions` list
 * (the no-scraping ToS posture; see test_extension_manifest.py). So the paste
 * draft is mirrored to localStorage on every keystroke and restored when the
 * popup reopens; it is cleared only once a capture succeeds or the user starts
 * a fresh one, so an error still leaves the text in place to retry.
 */
const DRAFT_TEXT_KEY = "fa.draft.jobText";
const DRAFT_URL_KEY = "fa.draft.sourceUrl";

function saveDraft() {
  try {
    localStorage.setItem(DRAFT_TEXT_KEY, jobTextInput.value);
    localStorage.setItem(DRAFT_URL_KEY, sourceUrlInput.value);
  } catch {
    /* private mode / storage disabled: persistence is best-effort. */
  }
}

function restoreDraft() {
  try {
    const text = localStorage.getItem(DRAFT_TEXT_KEY);
    const url = localStorage.getItem(DRAFT_URL_KEY);
    if (text) jobTextInput.value = text;
    if (url) sourceUrlInput.value = url;
  } catch {
    /* best-effort: an empty form is a fine fallback. */
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_TEXT_KEY);
    localStorage.removeItem(DRAFT_URL_KEY);
  } catch {
    /* nothing reachable to clean up. */
  }
}

jobTextInput.addEventListener("input", saveDraft);
sourceUrlInput.addEventListener("input", saveDraft);

/** The popup is only ever in exactly one of these. */
function showState(state) {
  form.hidden = state !== "form";
  pendingPanel.hidden = state !== "pending";
  errorPanel.hidden = state !== "error";
  resultPanel.hidden = state !== "result";
  submitButton.disabled = state === "pending";
}

function showError(message, detail) {
  errorMessage.textContent = message;
  if (detail) {
    errorDetail.textContent = detail;
    errorDetail.hidden = false;
  } else {
    errorDetail.hidden = true;
  }
  showState("error");
}

/**
 * Rendering lives in render_result.js, shared with the screenshot capture
 * window, so the two surfaces cannot disagree about what a verdict looks
 * like or about only ever using textContent for untrusted content.
 */
function renderResult(data) {
  FAResult.render(data, {
    badge: verdictBadge,
    score: scoreEl,
    reasoning: reasoningEl,
    extracted: extractedEl,
  });
  showState("result");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const rawText = jobTextInput.value.trim();
  if (!rawText) {
    showError("Paste a job posting first.");
    return;
  }

  const payload = { raw_text: rawText };
  const sourceUrl = sourceUrlInput.value.trim();
  if (sourceUrl) payload.source_url = sourceUrl;

  showState("pending");

  chrome.runtime.sendMessage({ type: "CAPTURE_JOB", payload }, (response) => {
    // A dead service worker or a listener that never replied surfaces here as
    // chrome.runtime.lastError rather than as a rejected promise.
    if (chrome.runtime.lastError) {
      showError(
        "The extension's background worker did not respond.",
        chrome.runtime.lastError.message,
      );
      return;
    }
    if (!response) {
      showError("The extension's background worker returned nothing.");
      return;
    }
    if (!response.ok) {
      // Keep the draft on error so the user can fix and retry without
      // re-pasting.
      showError(response.error, response.detail);
      return;
    }
    // The posting was captured successfully -- the draft has served its
    // purpose and would only reappear stale on the next open.
    clearDraft();
    renderResult(response.data);
  });
});

screenshotButton.addEventListener("click", () => {
  // A separate WINDOW, not a tab and not this popup: Chrome's share picker
  // takes focus, which destroys a popup mid-promise, and the user needs to
  // scroll the job page between shots with the capture controls still
  // visible. chrome.windows.create needs no permission.
  chrome.windows.create({
    url: chrome.runtime.getURL("capture.html"),
    type: "popup",
    width: 460,
    height: 720,
  });
  window.close();
});

retryButton.addEventListener("click", () => showState("form"));

newCaptureButton.addEventListener("click", () => {
  jobTextInput.value = "";
  sourceUrlInput.value = "";
  clearDraft();
  showState("form");
  jobTextInput.focus();
});

restoreDraft();
showState("form");
