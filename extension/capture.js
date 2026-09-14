/**
 * Screenshot capture window (CAP-04).
 *
 * WHY A FLOATING WINDOW AND NOT THE POPUP
 * ----------------------------------------
 * Two reasons, both fatal to doing this in the popup:
 *   1. `getDisplayMedia()` opens Chrome's picker, which takes focus — and an
 *      extension popup is destroyed the moment it loses focus, abandoning the
 *      promise. A real window survives.
 *   2. The user has to scroll the job page between captures. A popup closes
 *      as soon as they click the page; this window stays on top of it.
 *
 * WHY ONE SHARE SESSION, MANY SHOTS
 * ----------------------------------
 * The stream is opened once and held. Each "Capture this section" grabs a
 * frame from the live stream, so the user picks the tab a single time and
 * then just scrolls and clicks. Re-prompting per shot would make a
 * five-section posting a five-dialog chore.
 *
 * WHY THIS DOES NOT SCRAPE
 * -------------------------
 * No `tabs`, `activeTab`, `scripting` or `debugger` permission is involved,
 * and none is declared. `getDisplayMedia` shows Chrome's own picker; the user
 * explicitly chooses what to share and Chrome shows a sharing indicator the
 * whole time. The extension never reads the DOM, never navigates the page and
 * never scrolls it for the user — the user scrolls. That keeps PROJECT.md's
 * no-scraping stance intact while still getting the whole posting.
 */

const els = {
  stepHint: document.getElementById("step-hint"),
  startStep: document.getElementById("start-step"),
  startButton: document.getElementById("start-button"),
  shootingStep: document.getElementById("shooting-step"),
  preview: document.getElementById("preview"),
  shootButton: document.getElementById("shoot-button"),
  shotCount: document.getElementById("shot-count"),
  shots: document.getElementById("shots"),
  submitButton: document.getElementById("submit-button"),
  stopButton: document.getElementById("stop-button"),
  pending: document.getElementById("pending"),
  error: document.getElementById("error"),
  errorMessage: document.getElementById("error-message"),
  errorDetail: document.getElementById("error-detail"),
  retryButton: document.getElementById("retry-button"),
  result: document.getElementById("result"),
  badge: document.getElementById("verdict-badge"),
  score: document.getElementById("score"),
  reasoning: document.getElementById("reasoning"),
  extracted: document.getElementById("extracted"),
  newCaptureButton: document.getElementById("new-capture-button"),
};

/** Matches MAX_SCREENSHOTS in backend/tools/extract_from_screenshots.py. */
const MAX_SHOTS = 12;

let stream = null;
let shots = []; // ordered data URLs — order is the page's top-to-bottom order

function showState(state) {
  els.startStep.hidden = state !== "start";
  els.shootingStep.hidden = state !== "shooting";
  els.pending.hidden = state !== "pending";
  els.error.hidden = state !== "error";
  els.result.hidden = state !== "result";
}

function showError(message, detail) {
  els.errorMessage.textContent = message;
  if (detail) {
    els.errorDetail.textContent = detail;
    els.errorDetail.hidden = false;
  } else {
    els.errorDetail.hidden = true;
  }
  showState("error");
}

function stopSharing() {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
  els.preview.srcObject = null;
}

function renderShots() {
  els.shotCount.textContent = String(shots.length);
  els.submitButton.disabled = shots.length === 0;
  els.shootButton.disabled = shots.length >= MAX_SHOTS;
  els.stepHint.textContent =
    shots.length >= MAX_SHOTS
      ? `That is the maximum of ${MAX_SHOTS} sections. Run triage now.`
      : "Scroll the job page, then capture each section in order.";

  els.shots.replaceChildren();
  shots.forEach((dataUrl, index) => {
    const li = document.createElement("li");
    li.className = "shot";

    // The number is not decoration: these frames are read as one continuous
    // page in this order, so the user needs to see the order they built.
    const ordinal = document.createElement("span");
    ordinal.className = "shot__ordinal";
    ordinal.textContent = String(index + 1);

    const img = document.createElement("img");
    img.className = "shot__thumb";
    img.src = dataUrl;
    img.alt = `Captured section ${index + 1}`;

    const remove = document.createElement("button");
    remove.className = "button button--secondary shot__remove";
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      shots.splice(index, 1);
      renderShots();
    });

    li.append(ordinal, img, remove);
    els.shots.append(li);
  });
}

async function startSharing() {
  try {
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: 1 }, // a still capture needs no smooth video
      audio: false,
    });
  } catch (e) {
    // NotAllowedError is the user dismissing the picker — not a fault.
    if (e && e.name === "NotAllowedError") return;
    showError("Could not start screen sharing.", e && e.name);
    return;
  }

  // If the user ends sharing from Chrome's own indicator, reflect that here
  // rather than leaving a dead preview and a button that silently fails.
  stream.getVideoTracks().forEach((track) => {
    track.addEventListener("ended", () => {
      stopSharing();
      if (shots.length === 0) showState("start");
    });
  });

  els.preview.srcObject = stream;
  showState("shooting");
  renderShots();
}

function captureSection() {
  if (!stream) {
    showError("Sharing has stopped. Choose a tab to capture again.");
    return;
  }
  const video = els.preview;
  if (!video.videoWidth) {
    showError("The shared tab has not produced a frame yet — try again.");
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  shots.push(canvas.toDataURL("image/png"));
  renderShots();
}

function submit() {
  if (shots.length === 0) return;
  showState("pending");

  chrome.runtime.sendMessage(
    { type: "CAPTURE_SCREENSHOTS", payload: { screenshots: shots } },
    (response) => {
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
      FAResult.render(response.data, els);
      showState("result");
    },
  );
}

els.startButton.addEventListener("click", startSharing);
els.shootButton.addEventListener("click", captureSection);
els.submitButton.addEventListener("click", submit);
els.stopButton.addEventListener("click", () => {
  stopSharing();
  showState(shots.length ? "shooting" : "start");
});
els.retryButton.addEventListener("click", () => {
  showState(stream ? "shooting" : "start");
});
els.newCaptureButton.addEventListener("click", () => {
  shots = [];
  renderShots();
  showState(stream ? "shooting" : "start");
});

// Never leave a tab being shared after this window closes.
window.addEventListener("unload", stopSharing);

showState("start");
