# Freelance Autopilot — Chrome extension (capture client)

Manifest V3 popup that captures a job posting by **paste** and shows the Stage 1
triage verdict inline. Phase 4 of the roadmap (CAP-01, CAP-02, CAP-03).

## Load it

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** → select this `extension/` directory
4. Pin "Freelance Autopilot" to the toolbar and click it

## Point it at a backend

The popup POSTs to `http://localhost:8000/capture`, declared in
`manifest.json` under `host_permissions` and in `background.js` as
`BACKEND_ORIGIN`. **Change both together** — a fetch to an origin missing from
`host_permissions` is blocked by Chrome with a CORS error that looks like a
server problem but is not.

Phase 3 builds the real `/capture`. Until it exists, `dev/stub_capture_server.py`
stands in:

```bash
cd backend && .venv/bin/python ../extension/dev/stub_capture_server.py
```

That runs Phase 2's real `run_triage`, so gate-rejected postings work with no AWS
credentials. Add `--canned` to get a fixed apply verdict without calling Bedrock.

## Why the fetch lives in the service worker

Two reasons, both load-bearing:

- Under MV3, a request the service worker makes under a granted
  `host_permissions` entry is not subject to page CORS, so the backend needs no
  CORS cooperation.
- A popup's JS context is destroyed the moment the popup loses focus. A fetch
  started in `popup.js` would be aborted mid-flight when the user clicks away.

## No scraping, by construction

The extension declares **no** `tabs`, `activeTab`, `scripting` or
`content_scripts`. It cannot read the page you are on even if asked to — the
only source of job text is the textarea. The optional URL field is provenance
metadata that is never fetched. This is the Upwork-ToS constraint from
PROJECT.md, and `backend/tests/test_extension_manifest.py` fails the build if
any of it regresses.

## Files

| File | Role |
|---|---|
| `manifest.json` | MV3 manifest; the only place permissions are granted |
| `popup.html` / `styles.css` | Popup markup and styling (light + dark) |
| `popup.js` | Form → pending → result/error state machine |
| `background.js` | Service worker; the only code that talks to the backend |
| `dev/stub_capture_server.py` | Throwaway `/capture` stand-in — delete once Phase 3 lands |
