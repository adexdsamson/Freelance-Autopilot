# Phase 4 Plan: Chrome Extension Capture UI

**Requirements:** CAP-01, CAP-02, CAP-03
**Depends on:** Phase 3 (`/capture`) — **NOT YET BUILT**, see Dependency note
**Branch:** `gsd/phase-04-chrome-extension-capture-ui`

## Dependency note

Phase 4's whole purpose is to POST to `/capture`, which Phase 3 owns and which
does not exist. Rather than defer the phase, the extension was built against the
contract Phase 3 will implement and verified against
`extension/dev/stub_capture_server.py`, a throwaway stand-in that runs Phase 2's
real `run_triage`. Pointing the extension at the real endpoint is a no-op — same
URL, same shape. The stub is deleted when Phase 3 lands.

## Task Breakdown

### 04-01 — Manifest and service worker (CAP-02)
`manifest.json` (MV3, `host_permissions` scoped to the backend origin, no
scraping permissions) and `background.js` (top-level `onMessage` listener,
`AbortController` timeout, never-throwing result envelope).

### 04-02 — Popup (CAP-01, CAP-03)
`popup.html`, `styles.css`, `popup.js` — four-state machine, light+dark, all
untrusted text via `textContent`.

### 04-03 — Verification harness and tests
`dev/stub_capture_server.py`, `backend/tests/test_extension_manifest.py`,
`extension/README.md`.

## Success Criteria -> Verification

| # | Criterion | How it was verified |
|---|---|---|
| 1 | Paste-and-submit flow, no DOM scraping and no backend URL-fetch | Manifest declares no `tabs`/`activeTab`/`scripting`/`content_scripts` — asserted by test, so scraping is impossible rather than merely absent. URL field is metadata only |
| 2 | `background.js` POSTs to `/capture` and completes the round trip after a cold start | Round trip exercised in-browser against the stub, driving the **real** `background.js` and `popup.js`. Cold-start safety asserted structurally: the `onMessage` listener must be registered at column 0 |
| 3 | Explicit pending state, then verdict/score/reasoning inline | All four states rendered and screenshotted in-browser: form, pending, result (both `skip` and `apply`), error |

## Threat Model

| ID | Threat | Mitigation |
|---|---|---|
| T-04-01 | Pasted posting or model reasoning injected as markup into the popup | Everything reaches the DOM via `textContent`; `innerHTML`/`insertAdjacentHTML` absent, asserted by a comment-stripped source test |
| T-04-02 | Over-broad `host_permissions` (`<all_urls>`) grants reach beyond the demo backend | Exact-match assertion on the single localhost entry |
| T-04-03 | Cold-start listener registration regresses, popup hangs forever | Regex test anchored to column 0 |
| T-04-04 | A future edit adds a scraping permission and breaches Upwork ToS | Explicit deny-set test over `permissions` + `optional_permissions` |

## Out of Scope

`/capture` itself, auth, extension icons, capture history.
