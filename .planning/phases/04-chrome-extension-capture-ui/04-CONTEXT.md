# Phase 4: Chrome Extension Capture UI - Context

**Gathered:** 2026-09-09
**Status:** Executed

<domain>
## Phase Boundary

Ships the MV3 paste-capture popup (CAP-01, CAP-02, CAP-03). It does NOT build
`/capture` — that is Phase 3, which does not exist yet. The extension is written
against the contract Phase 3 will implement and verified against a throwaway
stub.

</domain>

<decisions>
## Implementation Decisions

- **D-17:** The extension POSTs `{raw_text, source_url?}`, not pre-parsed fields.
  Extraction is `extract_job_fields`' job (TRI-01) on the backend. A second
  parser in JS would drift from the Python one and break DEMO-02's identical-run
  requirement the moment the two disagree. — **Phase 3 must honour this shape.**
- **D-18:** No scraping capability is *declared*, rather than scraping merely
  being avoided: no `tabs`, `activeTab`, `scripting` or `content_scripts`. Chrome
  then makes DOM access impossible, which is a stronger guarantee than a code
  convention. A test fails the build if any appears.
- **D-19:** The optional URL field is provenance metadata, never fetched by
  either the popup or the backend — roadmap SC1 rules out a "backend URL-fetch
  convenience feature" as much as it rules out scraping.
- **D-20:** The fetch lives in the service worker, not the popup. Under
  `host_permissions` it bypasses page CORS, and it survives the popup closing —
  a popup's JS context is destroyed on blur, aborting any fetch started there.
- **D-21:** `popup.js` reads BOTH response shapes Phase 3 might return (verdict
  nested under `triage`, per PRD §6.2, or a bare `TriageResult`). Costs ~4 lines
  and means Phase 3 cannot break the popup by picking either.
- **D-22:** No API key. PRD §8 mentions "single local API key", but Phase 3 owns
  the endpoint's auth contract and does not exist yet; adding a header nothing
  validates is speculative. Flagged for Phase 3.

</decisions>

<canonical_refs>
## Canonical References

- `docs/PRD.md` §8 (extension spec), §12 (file layout), §6.2 (record shape)
- `.planning/REQUIREMENTS.md` — CAP-01, CAP-02, CAP-03
- `.planning/ROADMAP.md` Phase 4 — three success criteria
- `.claude/CLAUDE.md` §6 — MV3 `host_permissions` CORS bypass, why the fetch
  belongs in `background.js`, and why `<all_urls>` is wrong

</canonical_refs>

<code_context>
## Existing Code Insights

- Phase 2's `TriageResult` (`verdict`, `score`, `reasoning`, `extracted_fields`)
  is what the popup renders; `ExtractedJobFields.budget_type` is why the popup
  can show `$95/hr` rather than a bare `$95`.
- `run_triage` is reachable offline for gate-rejected postings, which is what
  lets the stub exercise a real end-to-end round trip with no AWS credentials.

</code_context>

<specifics>
## Specific Ideas

- MV3 cold start is the phase's real risk. A listener registered after an
  `await` is not attached when the worker respawns to handle the event that woke
  it, and the popup hangs forever. `chrome.runtime.onMessage.addListener` is
  therefore top-level and unindented, asserted by a regex test anchored to
  column 0.
- `[hidden] { display: none !important }` is load-bearing — `.panel`'s
  `display: flex` beats the `hidden` attribute otherwise. This shipped broken
  and was caught by rendering the popup, not by reading it.

</specifics>

<deferred>
## Deferred Ideas

- API key / auth header — Phase 3 owns the contract (D-22).
- Extension icons: none declared, so Chrome uses a default puzzle-piece. Cosmetic
  and Phase 7 polish.
- Capture history / re-open a past engagement — needs `GET /engagements/{id}`
  (Phase 3) and is not in CAP-01..03.

</deferred>

---

*Phase: 4-Chrome Extension Capture UI*
