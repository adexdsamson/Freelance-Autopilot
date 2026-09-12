---
phase: 06-ops-agent-fixtures-full-supervisor-wiring
plan: 02
subsystem: orchestration
tags: [strands-agents, agents-as-tools, supervisor, multi-agent, bedrock]

# Dependency graph
requires:
  - phase: 06-01
    provides: "OpsResult/ScopeCreepFlag/InvoiceFlag/StatusUpdate typed models, the three ops @tool functions, and _supervisor_ops_runner's lazy-import expectation of build_full_supervisor + extract_ops_result"
provides:
  - "build_ops_agent() -- the Ops specialist Agent (structured_output_model=OpsResult), the third specialist mirroring gig_triage_agent/proposal_contract_agent"
  - "build_full_supervisor() -- the unified Supervisor registering ALL THREE specialists (gig_triage_agent, proposal_contract_agent, ops_agent) as agents-as-tools, completing ORC-01/SC1"
  - "_find_tool_result_json + extract_ops_result -- the name-disambiguated two-pass toolResult extractor for multi-tool supervisor traces"
  - "backend/agents/ops_runner.py's _supervisor_ops_runner lazy import now resolves"
affects: [07-demo-packaging]

# Actuals (#2632)
actuals:
  tokens: 4399
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Name-disambiguated two-pass toolResult extraction (index toolUse.name->toolUseId, then filter toolResult by toolUseId) for a multi-tool supervisor trace, generalizing the Phase 3/5 first-json-block scan"
    - "Additive supervisor builder (build_full_supervisor) alongside stage-scoped supervisors (build_supervisor/build_proposal_supervisor) -- never mutating or deleting proven Phase 3/5 code"

key-files:
  created:
    - backend/agents/ops_agent.py
    - backend/tests/test_full_supervisor_wiring.py
  modified:
    - backend/agents/supervisor.py

key-decisions:
  - "extract_triage_result/extract_proposal_result were left completely untouched (RESEARCH Open Question 1 resolution) -- extract_ops_result is a new function built on a new shared _find_tool_result_json helper, added alongside rather than refactoring proven Phase 3/5 code."
  - "build_full_supervisor() is purely additive: a third builder function in supervisor.py, never modifying build_supervisor/build_proposal_supervisor -- proven by an explicit prohibition test asserting each stage-scoped supervisor keeps exactly its own single tool."
  - "Task 2's hardening/prohibition tests required zero production code changes -- the by-name two-pass extractor from Task 1 already disambiguates correctly and the two prior supervisor builders were never touched, so Task 2 committed as a single test-only commit per the plan action's explicit allowance."

patterns-established:
  - "Multi-tool supervisor trace disambiguation: never trust the first toolResult json block found once a supervisor holds more than one specialist tool -- always index toolUse.name->toolUseId first, then filter by that index."

requirements-completed: [ORC-01]

coverage:
  - id: D1
    description: "build_full_supervisor() registers all three specialist tools (gig_triage_agent, proposal_contract_agent, ops_agent) and yields four distinct Agent instances offline (ORC-01/SC1, D-01)"
    requirement: ORC-01
    verification:
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_build_full_supervisor_registers_all_three_specialist_tools"
        status: pass
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_four_distinct_agent_instances_exist"
        status: pass
    human_judgment: false
  - id: D2
    description: "extract_ops_result disambiguates the ops_agent toolResult by tool name from a multi-tool trace, never reading the Supervisor's own prose (ORC-01, D-01)"
    requirement: ORC-01
    verification:
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_extract_ops_result_disambiguates_by_name_among_multiple_toolresults"
        status: pass
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_extract_ops_result_ignores_supervisor_prose"
        status: pass
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_extract_ops_result_tolerates_malformed_content_blocks"
        status: pass
    human_judgment: false
  - id: D3
    description: "build_supervisor and build_proposal_supervisor remain single-tool and unchanged -- build_full_supervisor is purely additive (D-01 prohibition)"
    verification:
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_full_supervisor_does_not_mutate_stage_scoped_supervisors"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py::test_build_supervisor_unchanged_not_extended"
        status: pass
    human_judgment: false
  - id: D4
    description: "build_ops_agent constructs offline with no network call and sets structured_output_model=OpsResult (D-01, Pitfall 4)"
    verification:
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_build_ops_agent_returns_agent"
        status: pass
      - kind: unit
        ref: "backend/tests/test_full_supervisor_wiring.py::test_build_ops_agent_registers_three_tools"
        status: pass
    human_judgment: false
  - id: D5
    description: "The live four-agent Bedrock trace (OPS_BACKEND=supervisor, unified supervisor) shows four independently traceable Agent invocations"
    human_judgment: true
    rationale: "Sandbox has no real AWS Bedrock credentials (placeholder creds per STATE.md/D-08). This is documented MANUAL-only verification, same precedent as Phases 1/3/5 -- no automated test crosses the Bedrock boundary."
  - id: D6
    description: "ops_agent.py must not import the store (REC-03)"
    verification:
      - kind: unit
        ref: "backend/tests/test_single_writer.py::test_no_agent_or_tool_module_imports_store"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-08
status: complete
---

# Phase 6 Plan 02: Unified Three-Specialist Supervisor Summary

**A single `build_full_supervisor()` now registers all three specialists (gig_triage_agent, proposal_contract_agent, ops_agent) as agents-as-tools, with a name-disambiguated two-pass extractor (`extract_ops_result`) proving genuine multi-agent orchestration offline -- completing ORC-01.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-09-08T13:30:00Z (approx.)
- **Completed:** 2026-09-08T14:10:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `build_ops_agent()` (`backend/agents/ops_agent.py`) mirrors `proposal_contract_agent.py` exactly: wires the three ops tools (`check_scope_creep`, `check_invoice_status`, `draft_status_update`) plus `structured_output_model=OpsResult`, so the live toolResult path is guaranteed to emit typed json (Pitfall 4).
- `build_full_supervisor()` (`backend/agents/supervisor.py`) registers ALL THREE specialists on ONE Supervisor -- `supervisor.tool_names` contains `gig_triage_agent`, `proposal_contract_agent`, and `ops_agent`, and construction yields four distinct `Agent` instances (the supervisor plus the three specialists) -- proving ORC-01/SC1 offline, no Bedrock credentials required.
- `_find_tool_result_json(messages, tool_name)` generalizes the Phase 3/5 first-json-block scan into the two-pass toolUseId<->name disambiguation Phase 5 deferred: index every `toolUse` block by name -> toolUseId, then filter `toolResult` blocks by that index before reading the first `json` content block. `extract_ops_result` is built directly on top of it.
- `build_supervisor`/`build_proposal_supervisor`/`extract_triage_result`/`extract_proposal_result` are byte-for-byte unchanged -- proven by both the pre-existing `test_build_supervisor_unchanged_not_extended` and a new prohibition test asserting neither stage-scoped supervisor picked up `ops_agent` (or the other specialist's tool).
- `backend/agents/ops_runner.py`'s `_supervisor_ops_runner` lazy import (`from agents.supervisor import build_full_supervisor, extract_ops_result`) now resolves -- the `OPS_BACKEND=supervisor` live path is fully wired, pending only real AWS Bedrock credentials for manual verification.
- 10 new tests in `test_full_supervisor_wiring.py` cover construction (offline, no network), name-disambiguation against a multi-tool trace (the exact bug D-01 calls out), malformed-input tolerance, and the anti-mutation prohibition.

## Task Commits

Each task was committed following the RED/GREEN TDD cycle (Task 1) and a test-only commit (Task 2):

1. **Task 1 (tracer/tdd): build_ops_agent + build_full_supervisor + extract_ops_result, wired offline** - `303b30c` (test, RED) + `1a795e4` (feat, GREEN)
2. **Task 2 (auto/tdd, test-only): disambiguation hardening + prohibition tests** - `75743b4` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS)

## Files Created/Modified
- `backend/agents/ops_agent.py` - `build_ops_agent()`, the Ops specialist Agent (structured_output_model=OpsResult, no network at construction)
- `backend/agents/supervisor.py` - Adds `build_full_supervisor()`, `_find_tool_result_json()`, `extract_ops_result()`; `build_supervisor`/`build_proposal_supervisor`/`extract_triage_result`/`extract_proposal_result` untouched
- `backend/tests/test_full_supervisor_wiring.py` - 10 tests: construction (ops agent + full supervisor), four-distinct-instances, extraction (happy path, disambiguation among multiple toolResults, prose-ignoring, malformed-input tolerance, absent-raises), and the stage-scoped-supervisors-unmutated prohibition

## Decisions Made
- Left `extract_triage_result`/`extract_proposal_result` completely untouched rather than refactoring them to call the new shared `_find_tool_result_json` helper -- the safest reading of D-01's "keep intact" directive, zero risk to passing Phase 3/5 tests (RESEARCH Open Question 1 resolution, already decided at plan-authoring time).
- Task 2 committed as a single test-only commit rather than a RED/GREEN pair: the by-name two-pass extractor authored in Task 1 already disambiguates correctly, and the hardening/prohibition tests all passed against the existing implementation with zero production code changes -- exactly the outcome the plan action anticipated ("otherwise this task is test-only").
- Task 1's RED phase was verified explicitly: `backend/agents/ops_agent.py` was temporarily removed and `supervisor.py` reverted before the test file was committed, confirming a real `ModuleNotFoundError` (not a passing test) prior to the implementation commit.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched the plan's designed behavior; no Rule 1-4 auto-fixes were needed.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. The live `OPS_BACKEND=supervisor` / `build_full_supervisor()` four-agent Bedrock path remains manual-verification-only per D-08 (sandbox has placeholder AWS credentials, no real Bedrock access).

## Next Phase Readiness
- ORC-01, API-03, OPS-01..04, and DEMO-01 are all complete as of this plan (Phase 6 fully delivers its scope: unified 3-specialist supervisor + deterministic ops stage + fixtures).
- Phase 7 (demo packaging) can now write the README, demo script, architecture diagram, and OSI license, and run the deterministic end-to-end capture->proposal->ops walkthrough against the fixtures shipped in 06-01.
- The live four-agent Bedrock trace (`OPS_BACKEND=supervisor`, real AWS credentials) remains a manual verification step recommended before the final demo recording -- set `OPS_BACKEND=supervisor` + real credentials, run capture->proposal->ops, and inspect `supervisor.messages` for four distinct Agent invocations.
- No blockers. Full backend suite is green offline (118 tests passing before this plan's metadata commit).

## Self-Check: PASSED

- `backend/agents/ops_agent.py` — FOUND
- `backend/tests/test_full_supervisor_wiring.py` — FOUND
- `backend/agents/supervisor.py` (build_full_supervisor present) — FOUND
- Commit `303b30c` — FOUND in git log
- Commit `1a795e4` — FOUND in git log
- Commit `75743b4` — FOUND in git log
- Full suite: `cd backend && python3 -m pytest` — 118 passed
- `test_full_supervisor_wiring.py -q` — 10 passed
- `test_proposal_supervisor_wiring.py -q` + `test_supervisor_wiring.py -q` — all passing, unchanged
- `test_single_writer.py -q` — 1 passed (REC-03, ops_agent.py does not import the store)

---
*Phase: 06-ops-agent-fixtures-full-supervisor-wiring*
*Completed: 2026-09-08*
