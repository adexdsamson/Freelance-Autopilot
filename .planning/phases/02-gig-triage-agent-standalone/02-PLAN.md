# Phase 2 Plan: Gig Triage Agent (standalone)

**Requirements:** TRI-01, TRI-02, TRI-03, TRI-04
**Depends on:** Phase 1 (Engagement Record, store seam, verified Strands/Bedrock wiring)
**Branch:** `gsd/phase-02-gig-triage-agent`

## Goal

The Stage 1 specialist - deterministic gate followed by LLM judgement - works
correctly and repeatably against fixture jobs, independent of the Supervisor
or API.

## Task Breakdown

### 02-01 - Schemas and gate policy
- `backend/models/triage.py`: `ClientStats`, `ExtractedJobFields`,
  `KillSwitchResult`, `ScorecardJudgment`, `Scorecard`, `TriageResult`.
- `backend/tools/triage_config.py`: budget floors, two-tier client ladder,
  apply threshold, composite weights, red-flag phrases.

### 02-02 - The three tools
- `extract_job_fields` (TRI-01) - deterministic parse of pasted text.
- `kill_switch_check` (TRI-02) - deterministic gate, no network call.
- `llm_scorecard` (TRI-03) - real `BedrockModel` + `Agent.structured_output`.
- Seven fixture postings, each isolating one gate condition.

### 02-03 - The specialist and its runner
- `backend/agents/gig_triage_agent.py`: `GigTriageAgent.run` / `run_triage`.
- `backend/scripts/run_triage.py`: standalone CLI making SC4 executable.

## Success Criteria -> Verification

| # | Criterion | How it is verified |
|---|---|---|
| 1 | `extract_job_fields` returns title, description, budget, client stats | `tests/test_extract_job_fields.py` - 23 tests over 7 fixtures, incl. regressions for hourly-vs-fixed, client-spend-vs-budget, and verified-vs-not-verified misparses |
| 2 | `kill_switch_check` deterministically rejects/flags budget-floor, red-flag and weak-client fixtures, **with no LLM call** | `tests/test_kill_switch_check.py` - 21 tests under an autouse fixture that raises if `Agent`/`BedrockModel` is constructed |
| 3 | `llm_scorecard` produces a score and reasoning over fit, competition, rate | `tests/test_llm_scorecard.py` - 12 tests; Bedrock hop stubbed so composite arithmetic, D-06 wiring and flag propagation are asserted deterministically |
| 4 | Standalone run returns `{verdict, score, reasoning, extracted_fields}` with no escalation fields anywhere | `tests/test_gig_triage_agent.py` - 29 tests incl. a recursive key walk over the whole result and a schema-level assertion that escalation keys are rejected |

## Threat Model

| ID | Threat | Mitigation |
|---|---|---|
| T-02-01 | A raw Bedrock error message printed by the runner echoes request context or credentials | `scripts/run_triage.py` prints the exception *type name* only; regression-tested with a planted secret in the message |
| T-02-02 | `agents/` or `tools/` import the store, breaking REC-03/D-05 single-writer | Phase 1's AST import-graph test covers both new modules; still green |
| T-02-03 | Unstated client metadata read as passing values, letting a bad client through | Every field Optional; missing is always a flag (D-14), asserted by test |
| T-02-04 | A posting claiming ">100% hire rate" crashes `ClientStats`' `le=1.0` bound mid-demo | Parsed hire rate clamped to 1.0, with a test |

## Out of Scope

Supervisor wiring, `/capture`, the extension, Stage 2/3 fixtures, URL capture.
