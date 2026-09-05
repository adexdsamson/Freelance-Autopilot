---
phase: 05-proposal-contract-agent-advance-stage-proposal
plan: 2
subsystem: api
tags: [strands-agents, agents-as-tools, bedrock, engagement-record]

requires:
  - phase: 05-proposal-contract-agent-advance-stage-proposal
    provides: "ProposalContractResult/PaymentMilestone models, check_scope_clarity/draft_proposal/draft_contract tools, ProposalRunner DI seam with the _supervisor_proposal_runner lazy-import (Plan 05-01)"
provides:
  - "build_proposal_contract_agent: a real BedrockModel-backed Proposal-Contract specialist Agent, offline-constructible, registering check_scope_clarity/draft_proposal/draft_contract with structured_output_model=ProposalContractResult"
  - "build_proposal_supervisor: a stage-scoped Supervisor Agent wired to only the proposal_contract_agent tool via agents-as-tools (D-04), NOT an extension of build_supervisor()"
  - "extract_proposal_result: reads the specialist's typed toolResult json block from supervisor.messages, never the Supervisor's re-authored prose (D-02/ORC-02)"
affects: ["Phase 6 (stage=ops advancing, unified 3-agent Supervisor / ORC-01)"]

actuals:
  tokens: 3096
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Stage-scoped Supervisor builder (one tool per supervisor) instead of extending a shared multi-tool Supervisor, so extract_*_result's single toolResult scan can never disambiguate the wrong specialist (RESEARCH.md Pattern 3)"
    - "Specialist Agent construction performs no network call — only invocation touches Bedrock — proven by offline construction tests with placeholder AWS credentials (D-07f)"

key-files:
  created:
    - backend/agents/proposal_contract_agent.py
    - backend/tests/test_proposal_supervisor_wiring.py
  modified:
    - backend/agents/supervisor.py

key-decisions:
  - "build_proposal_supervisor is a wholly separate function from build_supervisor — the existing triage supervisor's tool_names is untouched (still exactly gig_triage_agent), matching D-04's explicit prohibition against a two-tool shared supervisor."
  - "extract_proposal_result is a byte-for-byte structural mirror of extract_triage_result (same isinstance guards, same RuntimeError-not-TypeError contract) so both extraction functions can never drift apart in behavior."

patterns-established:
  - "Two agents-as-tools Supervisor builders now coexist in one module (build_supervisor for triage, build_proposal_supervisor for proposal) as separate, single-tool functions — the template Phase 6 will follow if a third stage needs its own stage-scoped supervisor, or the pattern to explicitly break from if Phase 6 pursues ORC-01's unified three-agent Supervisor instead."

requirements-completed: [PROP-01, PROP-02, PROP-03, PROP-04]

coverage:
  - id: D1
    description: "build_proposal_contract_agent constructs offline (no AWS credentials, no network call) and registers exactly the three Plan 05-01 tools with structured_output_model=ProposalContractResult"
    requirement: "PROP-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_build_proposal_contract_agent_returns_agent"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_build_proposal_contract_agent_registers_three_tools"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_proposal_supervisor registers only proposal_contract_agent; build_supervisor is unchanged (still only gig_triage_agent) -- the stage-scoped-not-extended prohibition (D-04)"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_build_proposal_supervisor_registers_proposal_contract_agent_tool"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_build_supervisor_unchanged_not_extended"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_two_distinct_agent_instances_exist"
        status: pass
    human_judgment: false
  - id: D3
    description: "extract_proposal_result reads the typed toolResult json block for both happy-path and escalation payloads, ignores conflicting Supervisor prose, and raises RuntimeError (never TypeError) on absent/malformed blocks (D-02/ORC-02)"
    verification:
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_extract_proposal_result_reads_happy_path_tool_result_block"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_extract_proposal_result_reads_escalation_tool_result_block"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_extract_proposal_result_ignores_supervisor_prose"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_extract_proposal_result_raises_when_absent"
        status: pass
      - kind: unit
        ref: "backend/tests/test_proposal_supervisor_wiring.py#test_extract_proposal_result_tolerates_malformed_content_blocks"
        status: pass
    human_judgment: false
  - id: D4
    description: "REC-03 single-writer: proposal_contract_agent.py and the supervisor.py additions do not import the store"
    verification:
      - kind: unit
        ref: "backend/tests/test_single_writer.py#test_no_agent_or_tool_module_imports_store"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live two-agent Bedrock trace: two distinct Agent invocations (stage-scoped Supervisor + Proposal-Contract specialist) and the persisted proposal/contract slices matching the specialist's typed toolResult output verbatim"
    verification: []
    human_judgment: true
    rationale: "Requires real AWS/Bedrock credentials and a live PROPOSAL_BACKEND=supervisor invocation; the sandbox has only placeholder credentials, exactly as in Phases 1 and 3 -- this is documented as MANUAL-ONLY verification, never exercised by an automated test."

duration: ~15min
completed: 2026-09-05
status: complete
---

# Phase 5 Plan 2: Proposal-Contract Agent + Stage-Scoped Supervisor (live path) Summary

**A distinct, offline-constructible Proposal-Contract `Agent` wired into a stage-scoped `build_proposal_supervisor()` via agents-as-tools, plus `extract_proposal_result`'s typed toolResult channel — completing the seam Plan 05-01's `_supervisor_proposal_runner` lazy-imports, without extending the existing triage Supervisor or building Phase 6's unified three-agent Supervisor.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified/created:** 3 (1 modified, 2 created)

## Accomplishments
- Built `backend/agents/proposal_contract_agent.py`, mirroring `gig_triage_agent.py` exactly: a real `BedrockModel`-backed `Agent` that constructs with no network call, registers the three Plan 05-01 tools (`check_scope_clarity`, `draft_proposal`, `draft_contract`), and uses `structured_output_model=ProposalContractResult` — never the deprecated `Agent.structured_output()` method.
- Added `build_proposal_supervisor()` to `backend/agents/supervisor.py` as a wholly SEPARATE function from `build_supervisor()` — the stage-scoped Supervisor registers exactly one tool (`proposal_contract_agent`), keeping the existing triage Supervisor's `tool_names` untouched (D-04's explicit prohibition against a shared two-tool Supervisor).
- Added `extract_proposal_result`, a structural mirror of `extract_triage_result`: walks `supervisor.messages` for the first toolResult content block containing a `"json"` entry and validates it into `ProposalContractResult`, covering both the happy-path and escalation payload shapes, ignoring conflicting Supervisor prose, and raising `RuntimeError` (never a raw `TypeError`) on absent or malformed blocks.
- 10 new offline tests in `backend/tests/test_proposal_supervisor_wiring.py` prove offline construction, three-tool registration, single-tool stage-scoping (both supervisors verified NOT to cross-register the other's tool), two-distinct-instances (D-04), and all `extract_proposal_result` behaviors. Full suite: 76/76 passing offline with placeholder AWS credentials.
- Manually smoke-tested the wiring end-to-end offline: `build_proposal_supervisor().tool_names == ['proposal_contract_agent']`, `build_proposal_contract_agent().tool_names == ['check_scope_clarity', 'draft_proposal', 'draft_contract']`, and the two Agent instances are distinct objects.

## Task Commits

Each task was committed atomically:

1. **Task 1: build_proposal_contract_agent specialist (mirror build_gig_triage_agent)** - `8bdce40` (feat)
2. **Task 2: build_proposal_supervisor + extract_proposal_result (stage-scoped, single-tool)** - `ab90087` (feat)

**Plan metadata:** committed separately with this SUMMARY (docs commit).

## Files Created/Modified
- `backend/agents/proposal_contract_agent.py` - `MODEL_ID`/`REGION` env pattern, `build_proposal_contract_agent()` (offline-constructible, three tools, `structured_output_model=ProposalContractResult`)
- `backend/agents/supervisor.py` - added `build_proposal_supervisor()` + `extract_proposal_result()`; `build_supervisor()`/`extract_triage_result()` untouched
- `backend/tests/test_proposal_supervisor_wiring.py` - construction, registration, stage-scoping ("unchanged"), two-distinct-instances, and `extract_proposal_result` behavior coverage (happy path, escalation, prose-ignored, raises-when-absent, tolerates-malformed-blocks)

## Decisions Made
- `build_proposal_supervisor` is a wholly separate function from `build_supervisor`, never touching the latter's body — verified by an explicit "unchanged" test asserting each supervisor's `tool_names` contains only its own specialist.
- `extract_proposal_result` is a byte-for-byte structural mirror of `extract_triage_result` (identical isinstance guards, identical `RuntimeError`-not-`TypeError` contract on malformed input) so the two extraction functions cannot silently diverge in behavior over time.

## Deviations from Plan

None - plan executed exactly as written. Both tasks, their files, and their verification commands match the PLAN.md action items precisely; `_supervisor_proposal_runner`'s (Plan 05-01) lazy-imported names (`build_proposal_supervisor`, `extract_proposal_result`) now resolve correctly.

## Known Stubs

None — the live two-agent Bedrock path is fully wired and offline-provable; only its actual invocation against real Bedrock credentials remains manual-only (documented in the plan's `<verification>` section and in coverage item D5 above), exactly matching the Phase 1/Phase 3 precedent for live-path verification.

## Issues Encountered

None.

## User Setup Required

None for this plan's automated scope. To exercise the live two-agent Bedrock trace manually: export real AWS credentials + region, a valid Bedrock inference-profile model id, set `PROPOSAL_BACKEND=supervisor`, then POST /capture an apply-verdict job followed by POST /engagements/{id}/advance?stage=proposal.

## Next Phase Readiness

- Both Stage 1 (Gig Triage) and Stage 2 (Proposal-Contract) now have fully wired, offline-provable agents-as-tools paths behind their respective runner DI seams (`TriageRunner`/`ProposalRunner`), each with its own stage-scoped Supervisor.
- Full suite green (76/76) offline with placeholder AWS credentials; `test_single_writer.py` confirms no `agents/`/`tools/` module imports the store.
- Phase 6 can choose to either add a third stage-scoped supervisor (`build_ops_supervisor`, following this plan's pattern exactly) or pursue ORC-01's unified three-agent Supervisor as a deliberate architectural decision — this plan intentionally did NOT collapse the two existing stage-scoped supervisors into one, keeping that choice open and unforced.

---
*Phase: 05-proposal-contract-agent-advance-stage-proposal*
*Completed: 2026-09-05*

## Self-Check: PASSED

All 3 claimed files found on disk; both commit hashes (8bdce40, ab90087) found in git log.
