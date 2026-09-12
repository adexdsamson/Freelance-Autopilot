---
phase: 05-proposal-contract-agent-advance-stage-proposal
plan: 1
subsystem: api
tags: [fastapi, pydantic, strands-agents, engagement-record, deterministic-tools]

requires:
  - phase: 03-gig-triage-agent-capture-endpoint
    provides: "EngagementRecord/JobSlice/TriageSlice schema, FileEngagementStore, TriageRunner DI seam, map_bedrock_error 503 fail-fast, single-writer AST guard"
provides:
  - "PaymentMilestone + ProposalContractResult typed models with a mutual-exclusivity model_validator (D-01/D-06)"
  - "check_scope_clarity / draft_proposal / draft_contract dual-use @tool functions (PROP-01..04)"
  - "ProposalRunner DI seam (get_proposal_runner, PROPOSAL_BACKEND, default deterministic)"
  - "POST /engagements/{id}/advance?stage=proposal as the sole writer of the proposal/contract slices"
affects: ["Phase 6 (stage=ops advancing, unified 3-agent Supervisor)", "Plan 05-02 (live Bedrock proposal path)"]

actuals:
  tokens: 8336
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Mutually-exclusive structured result via Pydantic model_validator(mode='after') (D-01/SC2/SC3)"
    - "Deterministic-first DI seam + env-selected live path (ProposalRunner mirrors TriageRunner exactly)"
    - "Dual-use @tool functions (plain-Python + Agent-registered), single rule body"
    - "FastAPI-only VERBATIM merge of a specialist's typed result, no re-authoring"

key-files:
  created:
    - backend/tools/check_scope_clarity.py
    - backend/tools/draft_proposal.py
    - backend/tools/draft_contract.py
    - backend/agents/proposal_runner.py
    - backend/tests/test_advance_endpoint.py
    - backend/tests/test_proposal_runner.py
    - backend/tests/test_advance_bedrock_failfast.py
  modified:
    - backend/models/engagement_record.py
    - backend/api.py

key-decisions:
  - "PaymentMilestone.amount is an absolute dollar figure (0.3/0.5/0.2 split of budget, rounded to 2dp), not a fraction, per RESEARCH A2 and the plan's explicit instruction."
  - "check_scope_clarity's timeline/deliverables signals come from a keyword scan of job.description (no structured fields exist on JobSlice) — same keyword-scan shape as placeholder_kill_switch_check."
  - "409 for the non-apply/no-triage guard, 400 for an unsupported stage value — two distinct 4xx classes (resource-state vs request-shape), matching the plan/research recommendation."
  - "_supervisor_proposal_runner lazy-imports agents.supervisor.build_proposal_supervisor/extract_proposal_result (Plan 05-02's job) so this module stays importable before that code exists."

patterns-established:
  - "ProposalRunner Protocol + _deterministic_proposal_runner + _supervisor_proposal_runner + get_proposal_runner mirroring TriageRunner exactly, ready for Phase 6's stage=ops equivalent."
  - "advance() handler structured so Phase 6 adds an elif stage == \"ops\": branch without rewriting the guard/merge shape."

requirements-completed: [PROP-01, PROP-02, PROP-03, PROP-04]

coverage:
  - id: D1
    description: "Clear-scope apply engagement advances to a populated proposal + contract + typed payment schedule, verbatim through GET (SC1/SC4)"
    requirement: "PROP-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_clear_scope_returns_proposal_contract_and_round_trips"
        status: pass
    human_judgment: false
  - id: D2
    description: "draft_contract produces an SOW with enumerable deliverables and a structured, budget-summing payment schedule (PROP-02/PROP-03)"
    requirement: "PROP-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_draft_contract_enumerates_deliverables"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_draft_contract_payment_schedule_items_have_required_keys_and_sum_to_budget"
        status: pass
    human_judgment: false
  - id: D3
    description: "check_scope_clarity flags exactly the missing budget/timeline/deliverables fields and escalates via needs_human_input + a specific question, never raising (PROP-04/SC2)"
    requirement: "PROP-04"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_check_scope_clarity_cites_exact_missing_fields"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_deterministic_proposal_runner_escalates_on_ambiguous_job_without_raising"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_ambiguous_scope_escalates_and_round_trips"
        status: pass
    human_judgment: false
  - id: D4
    description: "ProposalContractResult structurally rejects both-populated and neither-populated constructions (SC3 mutual exclusivity)"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_exclusivity_rejects_both_populated"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_runner.py#test_exclusivity_rejects_neither_populated"
        status: pass
    human_judgment: false
  - id: D5
    description: "/advance guards: 404 unknown id, 409 no-triage/skip-verdict, 400 unsupported stage"
    verification:
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_unknown_engagement_returns_404"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_no_triage_returns_409"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_skip_verdict_returns_409"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_endpoint.py#test_advance_unsupported_stage_returns_400"
        status: pass
    human_judgment: false
  - id: D6
    description: "/advance fails fast + readably (503, never 500/200) on any injected proposal_runner failure, never leaking the raw AWS Message (D-07g)"
    verification:
      - kind: integration
        ref: "backend/tests/test_advance_bedrock_failfast.py#test_advance_maps_non_botocore_failures_to_503_not_500"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_bedrock_failfast.py#test_advance_returns_503_on_bedrock_client_error"
        status: pass
      - kind: integration
        ref: "backend/tests/test_advance_bedrock_failfast.py#test_advance_maps_no_credentials"
        status: pass
    human_judgment: false
  - id: D7
    description: "REC-03 single-writer: no new agents/tools module imports the store"
    verification:
      - kind: unit
        ref: "backend/tests/test_single_writer.py#test_no_agent_or_tool_module_imports_store"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-09-05
status: complete
---

# Phase 5 Plan 1: Proposal-Contract Agent + `/advance` (stage="proposal") Summary

**Deterministic proposal-contract drafting behind a `ProposalRunner` DI seam, exposed via `POST /engagements/{id}/advance?stage=proposal` as the sole writer of the proposal/contract slices, with a Pydantic `model_validator` structurally enforcing happy-path/escalation mutual exclusivity.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 completed
- **Files modified/created:** 9 (2 modified, 7 created)

## Accomplishments
- Enriched `EngagementRecord` with `PaymentMilestone` (typed payment-schedule line item) and `ProposalContractResult` (the specialist's one strict typed result, with a `model_validator(mode="after")` structurally enforcing SC3's happy-path/escalation mutual exclusivity); retyped `ContractSlice.payment_schedule` from `list[dict]` to `list[PaymentMilestone]` (D-06).
- Built the three PRD §7.2 dual-use `@tool` functions — `check_scope_clarity` (deterministic keyword-scan gate for missing budget/timeline/deliverables), `draft_proposal` (phased-scope template), `draft_contract` (SOW + a budget-summing three-milestone payment schedule) — none importing the store.
- Added `backend/agents/proposal_runner.py`, mirroring `triage_runner.py` exactly: a `ProposalRunner` Protocol, `_deterministic_proposal_runner` (composes the three tools as plain functions), `_supervisor_proposal_runner` (lazy-imports Plan 05-02's live path), and `get_proposal_runner` reading `PROPOSAL_BACKEND` (default deterministic).
- Wired `POST /engagements/{engagement_id}/advance` into `api.py`: 404 unknown id, 409 no-triage/non-apply, 400 unsupported stage, VERBATIM merge of the typed result into `proposal` (+ `contract` on the happy path), `store.save`, reusing `map_bedrock_error` unmodified for credential-free 503 fail-fast.
- 28 new tests across three files prove SC1 (clear-scope happy path + verbatim round-trip), SC2 (ambiguous escalation without exception), SC3 (mutual-exclusivity validator), SC4 (FastAPI-only verbatim merge), the 404/409/400 guard matrix, and 503-never-500 fail-fast with no credential/secret leakage. Full suite: 66/66 passing offline with placeholder AWS credentials.

## Task Commits

Each task was committed atomically:

1. **Task 1: TRACER — clear-scope /advance -> deterministic runner -> verbatim merge -> save, end-to-end** - `450e775` (feat)
2. **Task 2: Unit-depth — tools + deterministic runner + mutual-exclusivity (PROP-01..04, SC2, SC3)** - `7b9be63` (test)
3. **Task 3: Endpoint-contract depth — guards, verbatim merge (SC4), 503 fail-fast (D-07g)** - `bc977f5` (test)

**Plan metadata:** committed separately with this SUMMARY (docs commit).

## Files Created/Modified
- `backend/models/engagement_record.py` - `PaymentMilestone`, `ProposalContractResult` + mutual-exclusivity `model_validator`, retyped `ContractSlice.payment_schedule`
- `backend/tools/check_scope_clarity.py` - deterministic missing-budget/timeline/deliverables gate
- `backend/tools/draft_proposal.py` - phased-scope proposal template
- `backend/tools/draft_contract.py` - SOW + three-milestone typed payment schedule (absolute dollar amounts)
- `backend/agents/proposal_runner.py` - `ProposalRunner` DI seam, `PROPOSAL_BACKEND` env selection
- `backend/api.py` - `POST /engagements/{engagement_id}/advance` handler
- `backend/tests/test_advance_endpoint.py` - happy path + 404/409/400 guards + ambiguous-escalation round-trip + SC4 verbatim assertion
- `backend/tests/test_proposal_runner.py` - unit coverage of the three tools, the deterministic runner, the exclusivity validator, and env selection
- `backend/tests/test_advance_bedrock_failfast.py` - 503-never-500, no-secret-leak coverage mirroring `test_capture_bedrock_failfast.py`

## Decisions Made
- `PaymentMilestone.amount` is an absolute dollar figure (budget × 0.3/0.5/0.2, rounded to 2dp), matching the plan's explicit instruction over the RESEARCH.md code example's fraction-of-budget alternative.
- Kept `check_scope_clarity`'s timeline/deliverables signal as a keyword scan of `job.description` (no schema change to `JobSlice` — out of this plan's scope per RESEARCH Assumption A1).
- Used 409 for the non-apply/no-triage guard and 400 for an unsupported `stage` value, per the plan's and research's converged recommendation (resource-state vs request-shape 4xx classes).

## Deviations from Plan

None - plan executed exactly as written. All three tasks, their files, and their verification commands match the PLAN.md action items; the `_supervisor_proposal_runner` lazy import correctly references symbols (`build_proposal_supervisor`, `extract_proposal_result`) that Plan 05-02 will author, exactly as specified.

## Known Stubs

None — `_supervisor_proposal_runner`'s lazy import of `agents.supervisor.build_proposal_supervisor`/`extract_proposal_result` is an intentional forward reference to Plan 05-02 (the live Bedrock path), explicitly out of this plan's scope per 05-CONTEXT.md and never exercised by an automated test (manual-verification-only per D-07, matching Phase 3 precedent). This is not a stub blocking this plan's goal — the deterministic default path (this plan's actual deliverable) is fully wired and tested.

## Issues Encountered

None. One self-correction during Task 2: the initial `test_proposal_runner.py` test names for the SC3 mutual-exclusivity cases didn't include the word "exclusivity", so `pytest -k "exclusivity or ambiguous"` matched only 1 of 4 relevant tests instead of all 4 (RESEARCH's Test Map `-k` filter requirement). Renamed the three exclusivity tests to include "exclusivity" in their names before committing; re-verified `-k` selection matched 4 tests as required.

## User Setup Required

None - no external service configuration required. The deterministic default path (`PROPOSAL_BACKEND` unset) requires no AWS credentials.

## Next Phase Readiness

- `ProposalRunner`/`get_proposal_runner` and the `/advance` handler's `if stage != "proposal": raise HTTPException(400, ...)` guard are structured so Plan 05-02 (live Bedrock path) and Phase 6 (`stage="ops"`) extend in place without a rewrite.
- Full suite green (66/66) offline with placeholder AWS credentials; `test_single_writer.py` confirms no new `agents/`/`tools/` module imports the store.
- Plan 05-02 can now author `build_proposal_supervisor`/`extract_proposal_result` in `backend/agents/supervisor.py` and flip `PROPOSAL_BACKEND=supervisor` behind this already-tested seam.

---
*Phase: 05-proposal-contract-agent-advance-stage-proposal*
*Completed: 2026-09-05*

## Self-Check: PASSED

All 10 claimed files found on disk; all 4 commit hashes (450e775, 7b9be63, bc977f5, a88dfd8) found in git log.
