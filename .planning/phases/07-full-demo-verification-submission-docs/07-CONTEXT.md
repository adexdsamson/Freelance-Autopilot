# Phase 7: Full Demo Verification & Submission Docs - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning
**Mode:** Auto-generated (`--only 7`-style run; `--auto` discuss; decisions grounded in PRD §10, the DEMO-* requirements, and the integrated 1+3+5+6 stack present on this branch)

<domain>
## Phase Boundary

This phase makes the repository a **submittable hackathon entry** and proves the pipeline is
**deterministic and demo-ready**. It delivers **DEMO-02** (deterministic end-to-end run),
**DEMO-03** (README), **DEMO-04** (demo script + architecture diagram), and **DEMO-05**
(OSI license). No new agent behavior — this is verification tooling + submission docs over the
already-built multi-agent core.

**Stacked on `gsd/phase-06`** (branch `gsd/phase-07-full-demo-verification-submission-docs`
forked from `gsd/phase-06` @ 7c7bae7). That branch carries the full integrated stack: the
Engagement Record + store (Phase 1), the Gig Triage placeholder specialist + `/capture` (Phase 3),
the Proposal-Contract specialist + `/advance?stage=proposal` (Phase 5), and the Ops specialist +
`/advance?stage=ops` + unified `build_full_supervisor` + fixtures (Phase 6). 118 tests green offline.

**Scope decision on SC1 (extension-capture front).** ROADMAP lists Phase 7 as depending on
**Phase 4 (Chrome MV3 extension)**, which is **not built on any branch**. SC1's literal
"extension capture → triage → advance-to-proposal → advance-to-ops" therefore cannot be run
end to end with a real extension. This phase scopes the demo to the **integrated HTTP pipeline
that exists**: the "capture" step is the paste-to-`POST /capture` call the extension would itself
make. The extension front is documented as a **Phase 4 dependency**, not faked. Everything the
extension would post is exercised deterministically from `/capture` forward.

**Out of scope (belongs to other phases/engineers):**
- The Chrome MV3 extension itself (Phase 4, CAP-01..03) — separate track; a parallel session is
  also mid-build on the real Gig Triage tools (Phase 2) on the `gsd/phase-01` branch.
- Real Gig Triage LLM tools (TRI-01..04) — Phase 2; the deterministic placeholder stands in for
  the demo, keeping it repeatable and offline.
- AgentCore Memory/Runtime (DEPLOY-01/02) — Phase 8 (cut-first, depends on this phase).
- Recording the actual ≤5-minute video — a human action; this phase ships the *script* it follows.

</domain>

<decisions>
## Implementation Decisions

### DEMO-02 — deterministic end-to-end demo run (SC1, SC2)
- **D-01:** Ship a single runnable **demo entrypoint** — `backend/scripts/run_demo.py` — that drives
  the full pipeline **in-process via FastAPI `TestClient`** (no live server, no AWS creds, deterministic
  default backends): `POST /capture` → `POST /engagements/{id}/advance?stage=proposal` →
  `POST /engagements/{id}/advance?stage=ops`, for a selectable fixture, printing the Engagement Record
  progression (triage verdict, proposal/contract or escalation, ops escalation cards). "No manual glue
  steps" (SC1) = one command runs all stages. It reuses the existing app/DI seams — it does NOT add a
  second store writer (REC-03). — **Reversibility:** the entrypoint's CLI contract is what the demo
  script (D-04) references; keep it stable.
- **D-02:** DEMO-02 determinism (SC2) is proven by a **pytest test** `backend/tests/test_demo_determinism.py`
  that runs the full fixture set **three times** through the deterministic pipeline and asserts
  **identical** triage verdicts, proposal/escalation outcomes, and ops flags across all three runs
  (byte-for-byte on the record's decision fields). Offline, in the existing suite.

### DEMO-03 — README (SC3)
- **D-03:** Add a repo-root `README.md`: one-line project value; an architecture overview linking the
  diagram (D-05); setup (Python 3.10+, `pip install -r backend/requirements.txt` or the pinned deps,
  optional AWS-credential note for the live `*_BACKEND=supervisor` path); run instructions (the
  deterministic demo entrypoint + `uvicorn backend/api.py:app`); test instructions
  (`cd backend && python3 -m pytest`); a short requirements-traceability table; and the documented
  manual-only live-Bedrock/AgentCore boundaries. Must be accurate against the actual code (no invented
  commands/paths).

### DEMO-05 — OSI license (SC3)
- **D-04:** Add a repo-root **`LICENSE`** — **MIT** (PROJECT.md permits MIT or Apache-2.0; MIT is the
  shortest and satisfies the "visible OSI license in the About section" submission rule). Copyright line
  defaults to the repo owner / project (`Copyright (c) 2026 Freelance Autopilot`); the exact
  copyright-holder name is **user-adjustable** — flag it, do not put any email address in the file.

### DEMO-04 — architecture diagram + demo script (SC4)
- **D-05:** Add `docs/architecture.md` with a **Mermaid** diagram (renders natively on GitHub, no binary
  asset, diffable) that matches the **actual object graph** — verified against the real symbols, not
  invented: the MV3 extension (Phase 4, drawn as *planned/dashed*) → FastAPI endpoints
  (`/capture`, `GET /engagements/{id}`, `/advance?stage=proposal|ops`) as the **sole store writer** →
  `EngagementStore`/`FileEngagementStore`; the Supervisor (`build_full_supervisor`) orchestrating the
  three specialists (Gig Triage, Proposal-Contract, Ops) via **agents-as-tools**; and the DI runner
  seams (`TriageRunner`/`ProposalRunner`/`OpsRunner`, deterministic default + `*_BACKEND=supervisor`
  live path). The diagram must name symbols that exist in `backend/`.
- **D-06:** Add `docs/demo-script.md` — the **≤5-minute recorded-walkthrough script**: ordered
  narration + exact commands, driven by the D-01 entrypoint. Beats: (1) run the demo on the creep
  fixture → show triage `apply` verdict, proposal+contract, and **2** ops escalation cards; (2) run on
  the clean fixture → **0** ops cards (proves conditional, not hardcoded); (3) show an ambiguous
  proposal fixture → `needs_human_input` escalation; (4) note the live 4-agent Bedrock trace as the
  manual step. Ties every step to a real command.

### Verification strategy (offline-first, honest about the two manual boundaries)
- **D-07:** Offline tests MUST pass and verify: (a) SC2 determinism (3× identical) via
  `test_demo_determinism.py`; (b) SC1 pipeline end-to-end — the demo driver advances one record through
  all three stages in-process and asserts the record's triage/proposal/ops slices populate; (c) SC3
  presence — a test asserting repo-root `LICENSE` (OSI text) and `README.md` exist with the required
  sections; (d) SC4 presence — `docs/architecture.md` (with a mermaid block) and `docs/demo-script.md`
  exist. The **two genuine manual/out-of-scope items** — the real **Chrome-extension capture front**
  (Phase 4) and the **recorded video** — are documented as such, mirroring how the live-Bedrock traces
  were handled in Phases 1/3/5/6. Do not fabricate either.

### Claude's Discretion
- Exact demo-entrypoint CLI shape and flags; whether the determinism assertion compares full
  `model_dump()` decision fields or a curated subset; MIT copyright-holder string; diagram layout and
  level of detail; README section ordering; whether presence-tests live in one file or several.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (all on this branch)
- `backend/api.py` — FastAPI app (`/capture`, `GET /engagements/{id}`, `/advance?stage=proposal|ops`),
  the sole store writer; the demo driver calls it via `TestClient`.
- `backend/agents/{triage_runner,proposal_runner,ops_runner}.py` — DI seams, deterministic default →
  the demo runs offline with no creds.
- `backend/agents/supervisor.py` — `build_full_supervisor` (all three specialists) is the ORC-01
  artifact the diagram depicts.
- `backend/fixtures/` — `sample_client_thread(.json/_clean.json)`, `sample_payment_schedule(.json/_clean.json)`,
  `sample_upwork_jobs.json` + `loader.py`; the demo's deterministic inputs.
- `backend/tests/` — existing 118-test suite; the new determinism + presence tests join it.
- `docs/PRD.md`, `docs/COLLABORATION.md` — the diagram/README cross-reference these.

### Established Patterns to honor
- **Single-writer (REC-03):** the demo driver and any new scripts/tests MUST NOT import the store;
  only `api.py` writes it. (`test_single_writer.py` scans `agents/`+`tools/`+`fixtures/`.)
- **Deterministic default + env live path:** the demo uses the default (offline) backends.
- **Manual-only boundaries are documented, never faked** (live Bedrock trace precedent).

### Integration Points
- The demo entrypoint is the seam the demo-script and any future CI smoke test build on.
- README + LICENSE at repo root satisfy the submission "About section" rule.

</code_context>

<specifics>
## Specific Ideas
- SC2 (identical across 3 runs) is the anti-"nondeterministic demo" guard — assert on the record's
  decision fields, and keep any timestamps/UUIDs out of the compared subset.
- The architecture diagram is judged against the real object graph — build it from the actual
  `backend/` symbols (research/pattern-map will confirm), never from the PRD's aspirational shape.
- SC1's "no manual glue steps" is satisfied by the one-command entrypoint even though the extension
  front (Phase 4) is absent — the entrypoint posts exactly what the extension would.
</specifics>

<deferred>
## Deferred Ideas
- Chrome MV3 extension capture front (CAP-01..03) — Phase 4.
- Real Gig Triage LLM tools (TRI-01..04) — Phase 2 (parallel session in progress).
- Recording the actual video — human action after this phase ships the script.
- AgentCore Memory/Runtime (DEPLOY-01/02) — Phase 8.
</deferred>

---

*Phase: 7-Full Demo Verification & Submission Docs*
*Context gathered: 2026-09-09*
