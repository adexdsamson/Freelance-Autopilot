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
 * Accept either shape the backend might return.
 *
 * Phase 3 owns /capture's response and is not written yet. It may return the
 * whole EngagementRecord (verdict nested under `triage`, per PRD 6.2) or the
 * specialist's bare TriageResult (verdict at the top level). Reading both
 * costs a few lines here and means Phase 3 cannot break this popup by
 * choosing one over the other.
 */
function normalizeResult(data) {
  const triage = data && typeof data.triage === "object" && data.triage !== null ? data.triage : data;
  return {
    verdict: triage?.verdict ?? null,
    score: triage?.score ?? null,
    reasoning: triage?.reasoning ?? "",
    extracted: data?.extracted_fields ?? triage?.extracted_fields ?? data?.job ?? null,
    engagementId: data?.engagement_id ?? null,
  };
}

function formatBudget(extracted) {
  if (extracted.budget === null || extracted.budget === undefined) {
    return "not stated";
  }
  const amount = `$${Number(extracted.budget).toLocaleString()}`;
  return extracted.budget_type === "hourly" ? `${amount}/hr` : amount;
}

function formatClientStats(stats) {
  if (!stats || typeof stats !== "object") return null;
  const parts = [];
  if (stats.total_spend !== null && stats.total_spend !== undefined) {
    parts.push(`$${Number(stats.total_spend).toLocaleString()} spent`);
  }
  if (stats.hire_rate !== null && stats.hire_rate !== undefined) {
    parts.push(`${Math.round(stats.hire_rate * 100)}% hire rate`);
  }
  if (stats.payment_verified === true) parts.push("payment verified");
  if (stats.payment_verified === false) parts.push("payment NOT verified");
  return parts.length ? parts.join(" · ") : null;
}

function renderDefinition(term, value) {
  const dt = document.createElement("dt");
  dt.textContent = term;
  const dd = document.createElement("dd");
  // textContent, never innerHTML: the posting is untrusted pasted text and
  // the reasoning is model output. Neither is ever parsed as markup.
  dd.textContent = value;
  extractedEl.append(dt, dd);
}

function renderResult(data) {
  const { verdict, score, reasoning, extracted, engagementId } = normalizeResult(data);

  const verdictText = verdict ? String(verdict) : "unknown";
  verdictBadge.textContent = verdictText;
  verdictBadge.className = "badge";
  if (verdictText === "apply" || verdictText === "skip") {
    verdictBadge.classList.add(`badge--${verdictText}`);
  }

  scoreEl.textContent = score === null || score === undefined ? "" : `Score ${score}/100`;
  reasoningEl.textContent = reasoning || "No reasoning returned.";

  extractedEl.replaceChildren();
  if (extracted && typeof extracted === "object") {
    if (extracted.title) renderDefinition("Title", extracted.title);
    renderDefinition("Budget", formatBudget(extracted));
    const clientSummary = formatClientStats(extracted.client_stats);
    if (clientSummary) renderDefinition("Client", clientSummary);
  }
  if (engagementId) renderDefinition("Engagement", engagementId);

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
      showError(response.error, response.detail);
      return;
    }
    renderResult(response.data);
  });
});

retryButton.addEventListener("click", () => showState("form"));

newCaptureButton.addEventListener("click", () => {
  jobTextInput.value = "";
  sourceUrlInput.value = "";
  showState("form");
  jobTextInput.focus();
});

showState("form");
