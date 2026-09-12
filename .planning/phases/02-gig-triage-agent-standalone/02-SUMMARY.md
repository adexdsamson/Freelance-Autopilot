# Phase 2 Summary: Gig Triage Agent (standalone)

**Completed:** 2026-09-02
**Branch:** `gsd/phase-02-gig-triage-agent`
**Requirements delivered:** TRI-01, TRI-02, TRI-03, TRI-04

## What Was Built

| File | Purpose |
|---|---|
| `backend/models/triage.py` | Stage 1 contract: `ClientStats`, `ExtractedJobFields`, `KillSwitchResult`, `ScorecardJudgment`, `Scorecard`, `TriageResult` |
| `backend/tools/triage_config.py` | Every gate threshold in one screen: budget floors, two-tier client ladder, apply threshold, composite weights, red-flag phrases |
| `backend/tools/triage_tools.py` | The three `@tool` functions (TRI-01/02/03) |
| `backend/agents/gig_triage_agent.py` | `GigTriageAgent.run` / `run_triage` - the deterministic driver (TRI-04) |
| `backend/scripts/run_triage.py` | Standalone CLI making SC4 executable |
| `backend/tests/fixtures/jobs/*.txt` | Seven fixture postings, each isolating one gate condition |
| 5 test modules | 92 new tests |

## Success Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `extract_job_fields` returns title, description, budget, client stats | **Verified** | 23 tests over 7 fixtures |
| 2 | `kill_switch_check` deterministically rejects/flags, no LLM call | **Verified** | 21 tests; autouse fixture raises if `Agent`/`BedrockModel` is constructed |
| 3 | `llm_scorecard` produces score + reasoning over fit/competition/rate | **Verified (offline)** | 12 tests with the Bedrock hop stubbed - see Caveat |
| 4 | Standalone run returns the 4 fields, no escalation fields anywhere | **Verified** | 29 tests incl. recursive key walk + schema-level rejection |

Full suite: **106 passed** (14 from Phase 1, 92 new). Phase 1's REC-03/D-05
single-writer AST test still green against the new `agents/` and `tools/`
modules.

## Caveat - no live Bedrock call was made

This machine has no usable AWS credentials, so `llm_scorecard` has never run
against real Bedrock. Everything deterministic around it is genuinely tested:
composite arithmetic, the explicit model-id/region/`temperature=0` wiring
(D-06/D-12), that gate flags reach the prompt, and that the model is asked for
`ScorecardJudgment` (no `score` field). What remains unverified is the live
round trip - whether the pinned model id resolves in the configured region and
whether Claude fills the schema cleanly.

Verified failure behaviour instead: with credentials unset,
`python -m scripts.run_triage strong_fixed_apply` exits 1 with
`FAIL: triage could not complete (NoCredentialsError)...` and no traceback,
while `run_triage below_budget_floor` completes normally, because the gate
short-circuits before Bedrock.

**Before the demo recording**, run once with real credentials:

```bash
cd backend && python -m scripts.run_triage strong_fixed_apply
```

## Decisions Made

D-09 fixed-order driver (not a model-routed `Agent`), D-10 real Strands `Agent`
inside `llm_scorecard`, D-11 composite computed in code, D-12 `temperature=0`,
D-13 two-tier client ladder, D-14 missing metadata always flags, D-15
`budget_type` tracked, D-16 `extra="forbid"` on contracts but not on the
LLM-filled model. Full rationale in `02-CONTEXT.md`.

The one worth re-reading before Phase 3 is **D-09**: the specialist does not
register its tools on an `Agent` and let a model pick the order. Phase 3 wraps
`run_triage` in an `@tool` for the Supervisor - that is where agents-as-tools
lives - and the genuine second Agent invocation its SC4 looks for is the
`structured_output` call inside `llm_scorecard`.

## Handoff to Phase 3

- Wrap `run_triage(raw_text) -> TriageResult` in an `@tool`; it is the only
  entry point the Supervisor needs.
- The merge is a field copy, not a translation: `TriageResult.verdict/score/
  reasoning` are exactly `TriageSlice`'s fields, and `ExtractedJobFields` is
  field-compatible with `JobSlice` (`budget_type` is triage-side only and has
  no `JobSlice` counterpart by design).
- FastAPI does the merging. `agents/` and `tools/` still must not import the
  store.

## Notes

- `backend/.venv` (Python 3.11) is gitignored; system Python here is 3.9, below
  the project's 3.10 floor.
- TRI-01 says "text/URL"; only paste is implemented, per PROJECT.md's
  no-scraping constraint. URL capture is not planned for v1.
