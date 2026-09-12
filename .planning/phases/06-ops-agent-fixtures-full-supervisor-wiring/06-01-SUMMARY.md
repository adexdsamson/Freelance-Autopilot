---
phase: 06-ops-agent-fixtures-full-supervisor-wiring
plan: 01
subsystem: api
tags: [strands-agents, fastapi, pydantic, deterministic-tools, fixtures]

# Dependency graph
requires:
  - phase: 05-proposal-contract-agent-advance-endpoint
    provides: "/advance?stage=proposal, ProposalContractResult, ContractSlice, the ProposalRunner DI seam and map_bedrock_error 503 shape this plan mirrors for stage=ops"
provides:
  - "POST /engagements/{id}/advance?stage=ops&fixture=creep|clean completing API-03"
  - "OpsRunner DI seam (deterministic default, OPS_BACKEND=supervisor live path stub for Plan 06-02)"
  - "check_scope_creep / check_invoice_status / draft_status_update dual-use @tool functions (OPS-01/02/03)"
  - "Typed OpsResult/ScopeCreepFlag/InvoiceFlag/StatusUpdate models; OpsSlice retyped from list[dict] (D-07)"
  - "backend/fixtures/ creep+clean client-thread/payment-schedule fixtures + sample_upwork_jobs.json (DEMO-01)"
affects: [06-02-full-supervisor-wiring, 07-demo-packaging]

# Actuals (#2632)
actuals:
  tokens: 11251
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-use @tool functions (deterministic path + live specialist Agent) for the ops domain, mirroring Phase 5's check_scope_clarity/draft_proposal/draft_contract"
    - "OpsRunner Protocol + env-selected DI seam (OPS_BACKEND), mirroring ProposalRunner/TriageRunner exactly"
    - "Pure-data fixture loader (backend/fixtures/loader.py) with a creep/clean variant-suffix map, no store import"
    - "Explicit non-defaulted reference_date parameter for date-dependent determinism (never date.today() inside a tool)"

key-files:
  created:
    - backend/tools/check_scope_creep.py
    - backend/tools/check_invoice_status.py
    - backend/tools/draft_status_update.py
    - backend/fixtures/__init__.py
    - backend/fixtures/loader.py
    - backend/fixtures/sample_client_thread.json
    - backend/fixtures/sample_client_thread_clean.json
    - backend/fixtures/sample_payment_schedule.json
    - backend/fixtures/sample_payment_schedule_clean.json
    - backend/fixtures/sample_upwork_jobs.json
    - backend/agents/ops_runner.py
    - backend/tests/test_ops_tools.py
    - backend/tests/test_ops_runner.py
    - backend/tests/test_fixtures_loader.py
  modified:
    - backend/models/engagement_record.py
    - backend/api.py
    - backend/tests/test_advance_endpoint.py
    - backend/tests/test_advance_bedrock_failfast.py

key-decisions:
  - "check_invoice_status takes a required reference_date parameter with no default and never reads the wall clock; fixtures use absolute already-past (2025-01-15) and far-future (2099-01-15) ISO dates so SC2/SC3 stay deterministic indefinitely (Pitfall 1)."
  - "The /advance fixture query param is typed Literal[\"creep\",\"clean\"] so FastAPI structurally 422s any other value, mirroring engagement_id:UUID's existing path-traversal closure (T-06-PT)."
  - "The ops branch reuses map_bedrock_error VERBATIM for its 503 path — no parallel error mapper (T-06-LEAK)."
  - "OpsSlice/OpsResult field names (status_updates/scope_creep_flags/invoice_flags) kept unchanged while retyping from list[dict] to typed Pydantic lists (D-07), so the persisted record shape and Plan 06-02's extractor stay compatible."

patterns-established:
  - "Ops-domain payment schedule ({label, amount, due_date, paid}) is a distinct schema from ContractSlice.PaymentMilestone ({label, amount, due_marker}) — never conflate the two (Pitfall 2)."

requirements-completed: [API-03, OPS-01, OPS-02, OPS-03, OPS-04, DEMO-01]

coverage:
  - id: D1
    description: "Capture->proposal->ops runs end-to-end offline for the creep fixture, returning exactly 2 escalation cards and persisting the ops slice (API-03/SC5, D-05)"
    requirement: API-03
    verification:
      - kind: e2e
        ref: "backend/tests/test_advance_endpoint.py#test_advance_ops_after_proposal_completes_both_stages"
        status: pass
    human_judgment: false
  - id: D2
    description: "The clean fixture variant yields exactly 0 escalation cards through the SAME OpsRunner code path that yields 2 on creep (SC3, D-06)"
    requirement: OPS-04
    verification:
      - kind: unit
        ref: "backend/tests/test_ops_runner.py#test_deterministic_ops_runner_clean_fixture_yields_zero_cards"
        status: pass
      - kind: unit
        ref: "backend/tests/test_ops_runner.py#test_deterministic_ops_runner_creep_fixture_yields_two_cards"
        status: pass
    human_judgment: false
  - id: D3
    description: "draft_status_update's text reflects whichever flags are currently active, or states the engagement is on track when none are (OPS-03/SC4)"
    requirement: OPS-03
    verification:
      - kind: unit
        ref: "backend/tests/test_ops_tools.py -k status_update"
        status: pass
    human_judgment: false
  - id: D4
    description: "check_scope_creep and check_invoice_status independently detect exactly the fixture-designed creep message and overdue milestone, and zero on the clean variants (OPS-01/OPS-02)"
    requirement: OPS-01
    verification:
      - kind: unit
        ref: "backend/tests/test_ops_tools.py -k scope_creep"
        status: pass
      - kind: unit
        ref: "backend/tests/test_ops_tools.py -k invoice_status"
        status: pass
    human_judgment: false
  - id: D5
    description: "Advancing to stage=ops without a signed contract, or after an escalated proposal, returns 409; an out-of-set fixture value returns 422 (Pitfall 3/T-06-PT)"
    verification:
      - kind: e2e
        ref: "backend/tests/test_advance_endpoint.py#test_advance_ops_without_contract_returns_409"
        status: pass
      - kind: e2e
        ref: "backend/tests/test_advance_endpoint.py#test_advance_ops_when_proposal_escalated_returns_409"
        status: pass
      - kind: e2e
        ref: "backend/tests/test_advance_endpoint.py#test_advance_ops_out_of_set_fixture_returns_422"
        status: pass
    human_judgment: false
  - id: D6
    description: "The ops branch's 503 path reuses map_bedrock_error verbatim; no raw AWS Message/secret leaks into the response detail (D-08(g)/T-06-LEAK)"
    verification:
      - kind: e2e
        ref: "backend/tests/test_advance_bedrock_failfast.py -k ops"
        status: pass
    human_judgment: false
  - id: D7
    description: "None of the new ops tools, the fixture loader, or ops_runner import the store (REC-03/D-02)"
    requirement: OPS-01
    verification:
      - kind: unit
        ref: "backend/tests/test_single_writer.py#test_no_agent_or_tool_module_imports_store"
        status: pass
    human_judgment: false
  - id: D8
    description: "Fixtures load deterministically and the creep/clean variant selector produces the two documented states, including the DEMO-01 jobs fixture (DEMO-01/D-04)"
    requirement: DEMO-01
    verification:
      - kind: unit
        ref: "backend/tests/test_fixtures_loader.py"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-08
status: complete
---

# Phase 6 Plan 01: Ops Stage (Deterministic) Summary

**Deterministic Ops stage wired end-to-end through `/advance?stage=ops`: three dual-use tools (scope-creep, overdue-invoice, status-update), a creep/clean fixture set, an `OpsRunner` DI seam, and typed escalation cards proving 2 cards on creep vs. 0 on clean through one code path.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-09-08T13:00:00Z (approx.)
- **Completed:** 2026-09-08T13:30:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments
- `POST /engagements/{id}/advance?stage=ops&fixture=creep|clean` completes API-03: one engagement now advances through `stage=proposal` then `stage=ops`, each call returning the updated, persisted record.
- Three deterministic, dual-use `@tool` functions (`check_scope_creep`, `check_invoice_status`, `draft_status_update`) are the single source of truth for OPS-01/02/03, callable both as plain Python (deterministic default) and as tools on a future live Ops specialist Agent (Plan 06-02).
- The creep+overdue fixture yields exactly 2 escalation cards (1 scope-creep + 1 invoice) and the clean fixture yields exactly 0, through the SAME `_deterministic_ops_runner` code path — proving the checks are conditional, not hardcoded (SC2/SC3/D-06).
- `OpsSlice`/new `OpsResult` typed models (`ScopeCreepFlag`, `InvoiceFlag`, `StatusUpdate`) replace the Phase-1 `list[dict]` stub, keeping field names unchanged (D-07).
- The ops branch's precondition (409), input-validation (422 on the `Literal["creep","clean"]` fixture param), and Bedrock fail-fast (503, `map_bedrock_error` reused verbatim) contracts are fully covered offline.
- `backend/fixtures/` now ships the full DEMO-01 set: creep/clean client-thread and payment-schedule pairs plus a 7-posting `sample_upwork_jobs.json`.

## Task Commits

Each task was committed atomically (Task 2 followed the RED/GREEN TDD cycle):

1. **Task 1 (tracer): capture->proposal->ops end-to-end for the creep variant** - `4ca87ce` (feat)
2. **Task 2 (tdd): clean-variant conditional depth** - `baa531f` (test, RED) + `86578f4` (feat, GREEN)
3. **Task 3: endpoint-contract depth (409/422/503) + jobs fixture** - `3fc8049` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

## Files Created/Modified
- `backend/models/engagement_record.py` - Adds `ScopeCreepFlag`/`InvoiceFlag`/`StatusUpdate`/`OpsResult`; retypes `OpsSlice` fields from `list[dict]` to typed lists
- `backend/tools/check_scope_creep.py` - OPS-01 deterministic creep-signal-phrase gate vs. signed SOW text
- `backend/tools/check_invoice_status.py` - OPS-02 deterministic overdue gate, explicit `reference_date`, never the wall clock
- `backend/tools/draft_status_update.py` - OPS-03/SC4 deterministic client-ready status template
- `backend/fixtures/__init__.py`, `backend/fixtures/loader.py` - Pure-data loader, creep/clean variant selector, jobs loader
- `backend/fixtures/sample_client_thread.json` (+ `_clean`), `sample_payment_schedule.json` (+ `_clean`), `sample_upwork_jobs.json` - DEMO-01 fixture set
- `backend/agents/ops_runner.py` - `OpsRunner` Protocol, deterministic + lazy-imported live path, `OPS_BACKEND` env switch
- `backend/api.py` - `elif stage == "ops":` branch: 409 precondition guard, `fixture: Literal["creep","clean"]` param, `map_bedrock_error`-based 503, VERBATIM merge into `record.ops`
- `backend/tests/test_ops_tools.py`, `test_ops_runner.py`, `test_fixtures_loader.py` - New unit coverage for the tools, runner, and loader
- `backend/tests/test_advance_endpoint.py` - Fixed the now-stale unsupported-stage test; added the proposal->ops progression, 409, and 422 tests
- `backend/tests/test_advance_bedrock_failfast.py` - Added `-k ops` 503 coverage (NoCredentialsError/ClientError/RuntimeError)

## Decisions Made
- `check_invoice_status`'s `reference_date` is required with no default, and fixture due dates are absolute ISO dates (2025-01-15 past / 2099-01-15 future) so the demo and test suite never depend on wall-clock timing (Pitfall 1).
- The `fixture` query param on `/advance` is a closed `Literal["creep","clean"]`, structurally rejecting any other value with a 422 rather than interpolating a raw string into a fixture filename (T-06-PT).
- The ops-stage payment schedule (`label`/`amount`/`due_date`/`paid`) is kept as a distinct schema from `ContractSlice.PaymentMilestone` (`label`/`amount`/`due_marker`) — the two are never conflated (Pitfall 2).
- `OpsSlice`/`OpsResult` field names were kept identical while retyping from `list[dict]` to typed Pydantic lists, so the persisted record shape and Plan 06-02's forthcoming supervisor extractor remain compatible (D-07).

## Deviations from Plan

None - plan executed exactly as written. All three tasks (including the Task 2 TDD RED/GREEN cycle) matched the plan's designed behavior; no Rule 1-4 auto-fixes were needed.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. The deterministic ops path never touches Bedrock; the live `OPS_BACKEND=supervisor` path is deferred to Plan 06-02 and remains manual-verification-only per D-08.

## Next Phase Readiness
- Plan 06-02 (unified 3-specialist Supervisor, ORC-01) can now build `build_full_supervisor()` and `extract_ops_result` against this plan's `OpsResult`/`OpsSlice` typed models and the `_supervisor_ops_runner` lazy-import seam already stubbed in `ops_runner.py`.
- No blockers. Full backend suite is green offline (108 tests passing before this plan's metadata commit).

## Self-Check: PASSED

- `backend/agents/ops_runner.py` — FOUND
- `backend/fixtures/loader.py` — FOUND
- `backend/fixtures/sample_client_thread.json` — FOUND
- `backend/fixtures/sample_client_thread_clean.json` — FOUND
- `backend/fixtures/sample_payment_schedule.json` — FOUND
- `backend/fixtures/sample_payment_schedule_clean.json` — FOUND
- `backend/fixtures/sample_upwork_jobs.json` — FOUND
- `backend/tools/check_scope_creep.py` — FOUND
- `backend/tools/check_invoice_status.py` — FOUND
- `backend/tools/draft_status_update.py` — FOUND
- Commit `4ca87ce` — FOUND in git log
- Commit `baa531f` — FOUND in git log
- Commit `86578f4` — FOUND in git log
- Commit `3fc8049` — FOUND in git log
- Full suite: `cd backend && python3 -m pytest` — 108 passed
- `test_advance_endpoint.py -q` — 12 passed (includes SC2/SC5/409/422 ops tests)
- `test_advance_bedrock_failfast.py -k ops -q` — 3 passed
- `test_single_writer.py -q` — 1 passed (REC-03, no ops module imports the store)

---
*Phase: 06-ops-agent-fixtures-full-supervisor-wiring*
*Completed: 2026-09-08*
