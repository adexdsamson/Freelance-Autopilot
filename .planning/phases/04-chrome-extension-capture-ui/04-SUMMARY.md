# Phase 4 Summary: Chrome Extension Capture UI

**Completed:** 2026-09-09
**Branch:** `gsd/phase-04-chrome-extension-capture-ui`
**Requirements delivered:** CAP-01, CAP-02, CAP-03

## What Was Built

| File | Purpose |
|---|---|
| `extension/manifest.json` | MV3 manifest — the only place permissions are granted |
| `extension/background.js` | Service worker; the only code that talks to the backend |
| `extension/popup.html` / `styles.css` | Popup markup, light + dark |
| `extension/popup.js` | form → pending → result/error state machine |
| `extension/README.md` | Load instructions and the origin-change gotcha |
| `extension/dev/stub_capture_server.py` | Throwaway `/capture` stand-in |
| `backend/tests/test_extension_manifest.py` | 11 structural tests |

Full suite: **117 passed** (106 from Phases 1-2, 11 new).

## Success Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Paste flow, no DOM scraping, no URL-fetch | **Verified** | Manifest declares no `tabs`/`activeTab`/`scripting`/`content_scripts`; deny-set test |
| 2 | Service worker POSTs to `/capture`, round trip survives cold start | **Verified against a stub** — see Caveat | Round trip driven in-browser through the real `background.js`; listener-at-column-0 asserted |
| 3 | Explicit pending state, then verdict/score/reasoning inline | **Verified** | All four states rendered in-browser; `skip` and `apply` both checked, light and dark |

## Caveat — the round trip was verified against a stub, not Phase 3

Phase 3 does not exist, so `/capture` was stood up as
`extension/dev/stub_capture_server.py`. The extension code under test was the
real thing — the browser harness loaded the shipped `background.js` and
`popup.js` unmodified — but the server on the other end was not.

What that leaves unproven:

- **The real cold start.** SC2 asks for a round trip with DevTools closed after
  30s idle, in Chrome, with the extension actually installed. The harness ran in
  a normal tab, so it exercised the listener logic but not Chrome's genuine
  service-worker teardown. The structural rule that makes cold start work is
  asserted by test; the observed behaviour is not.
- **Phase 3's actual response shape.** `popup.js` reads both plausible shapes
  (D-21), so it should survive either, but "should" is doing work there.

**To close both:** once Phase 3 lands, load the extension unpacked, run a real
capture, then leave it idle >30s with DevTools closed and capture again.

## Decisions Made

D-17 POST `{raw_text}` not pre-parsed fields, D-18 no scraping capability
declared, D-19 URL is provenance only, D-20 fetch in the service worker, D-21
popup reads both response shapes, D-22 no API key yet. Rationale in
`04-CONTEXT.md`.

## One bug found and fixed during verification

The popup shipped with the pending and error panels rendering on top of the form
in every state: `.panel { display: flex }` beats the `hidden` attribute's UA
`display: none`. Fixed with `[hidden] { display: none !important }`. It was
invisible in code review and obvious on first render — the reason this phase was
verified by looking at it rather than only reading it.

## Handoff to Phase 3

Phase 3 owns `/capture` and must match what the extension already sends:

- **Request:** `POST /capture`, `Content-Type: application/json`, body
  `{"raw_text": "<the paste>", "source_url": "<optional>"}`. Extraction is the
  backend's job (TRI-01) — the extension deliberately sends no parsed fields.
- **Response:** 2xx JSON. Either `{engagement_id, job, triage:{verdict, score,
  reasoning}, extracted_fields}` or a bare `TriageResult` will render.
- **Auth:** none currently sent (D-22). If Phase 3 adds a key, `background.js`
  needs the header and `README.md` needs the note.
- **CORS:** not required for the extension, whose service worker bypasses it
  under `host_permissions`. Add it anyway for browser-tab debugging.
- Delete `extension/dev/stub_capture_server.py` once the real endpoint exists.
