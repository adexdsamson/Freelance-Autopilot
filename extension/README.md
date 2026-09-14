# Freelance Autopilot — Chrome extension (capture client)

Manifest V3 popup that captures a job posting and shows the Stage 1 triage
verdict inline. Two capture modes (CAP-01..CAP-04):

- **Paste** — paste the posting text. Extraction is the deterministic regex
  parser, so this is the demo and fixture path (DEMO-02).
- **Screenshots** — click *Capture with screenshots*. A small window opens, you
  pick the tab via Chrome's own share picker, then grab each section of the
  posting as you scroll. Every frame goes to Claude in one call and is read as
  a single continuous page. Extraction is a vision call and therefore **not**
  deterministic, which is why it is kept off the demo path.

## Load it

1. Open `chrome://extensions`
2. Turn on **Developer mode** (top right)
3. **Load unpacked** → select this `extension/` directory
4. Pin "Freelance Autopilot" to the toolbar and click it

## Point it at a backend

Paste mode POSTs to `/capture/text`; screenshot mode to `/capture/screenshots`.
Both are on `http://localhost:8000`, declared in
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

The extension declares **no** `tabs`, `activeTab`, `scripting`, `debugger` or
`content_scripts` — in fact its `permissions` array is empty. It cannot read
the DOM of the page you are on even if asked to.

Screenshot mode does not change that, which was the whole point of how it was
built. It uses `getDisplayMedia()`, so **Chrome's own picker** asks which
surface to share, Chrome shows a sharing indicator throughout, and the
extension only ever receives a video frame — never the page.

The extension also never scrolls the page for you. That is why capture is
multi-shot: the two ways to get a true single-image full-page capture are a
`scripting`-injected scroll-and-stitch, or `debugger` +
`captureBeyondViewport`, and both would have reversed PROJECT.md's no-scraping
decision (the second also puts a "being debugged" banner on screen). You
scroll; the extension captures.

`backend/tests/test_extension_manifest.py` fails the build if any of this
regresses, including a test asserting the permission list is still empty.

## Files

| File | Role |
|---|---|
| `manifest.json` | MV3 manifest; the only place permissions are granted |
| `popup.html` / `styles.css` | Popup markup and styling (light + dark) |
| `popup.js` | Paste mode: form → pending → result/error state machine |
| `capture.html` / `capture.js` | Screenshot mode: share picker, multi-section capture |
| `render_result.js` | Verdict rendering, shared by both modes |
| `background.js` | Service worker; the only code that talks to the backend |
| `dev/stub_capture_server.py` | Throwaway `/capture` stand-in — delete once Phase 3 lands |
