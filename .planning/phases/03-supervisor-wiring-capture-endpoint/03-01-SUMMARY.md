---
phase: 03-supervisor-wiring-capture-endpoint
plan: 01
subsystem: api
tags: [strands-agents, fastapi, pydantic, bedrock, agents-as-tools, structured-output]

requires:
  - phase: 01-foundations-engagement-record-strands-bedrock-verification-spike
    provides: EngagementRecord/JobSlice/TriageSlice schema, EngagementStore/FileEngagementStore, Bedrock error taxonomy, single-writer guard
provides:
  - "Real Supervisor Agent wrapping a Gig Triage specialist Agent via the verified agents-as-tools pattern (two distinct Agent instances)"
  - "extract_triage_result(): reads the specialist's toolResult json content block verbatim, ignoring Supervisor prose (ORC-02)"
  - "POST /capture: JobSlice in -> triage via TriageRunner DI seam -> persist -> verdict out"
  - "GET /engagements/{id}: read-through with 404 for unknown ids"
  - "TriageRunner DI seam (TRIAGE_BACKEND env flag) that Phase 2 will retarget without touching Supervisor/API code"
  - "Deterministic placeholder_kill_switch_check tool: budget-floor + red-flag-keyword gate, Phase-2 stand-in"
  - "Bedrock fail-fast: /capture returns a readable, credential-free 503 instead of a raw 500"
affects: [04-chrome-extension-capture-integration, 05-proposal-contract-agent, phase-2-real-triage-tools]

actuals:
  tokens: 6454
  tasks: 5
  commits: 6

tech-stack:
  added: [fastapi>=0.141,<0.142, "uvicorn[standard]>=0.52,<0.53", httpx]
  patterns:
    - "Agents-as-tools: specialist Agent wrapped with .as_tool(delegate=True), registered on the Supervisor's tools=[...]"
    - "Typed-channel merge: read the toolResult 'json' content block directly from supervisor.messages, never the Supervisor's own final text (structured_output_model + .as_tool() emit it before delegate logic runs)"
    - "TriageRunner DI seam: a Protocol + env-flag-selected implementation, injected into FastAPI via Depends() and overridable via app.dependency_overrides in tests"
    - "Single source of truth for the placeholder rule: one @tool-decorated plain function, called directly (offline path) or registered as an Agent tool (live path) -- @tool preserves normal callability"
    - "FastAPI as sole store writer: only api.py imports store.*, enforced by the existing AST-based test_single_writer.py"

key-files:
  created:
    - backend/api.py
    - backend/agents/supervisor.py
    - backend/agents/gig_triage_agent.py
    - backend/agents/triage_runner.py
    - backend/tools/placeholder_triage.py
    - backend/tests/test_capture_endpoint.py
    - backend/tests/test_engagements_endpoint.py
    - backend/tests/test_triage_runner.py
    - backend/tests/test_supervisor_wiring.py
    - backend/tests/test_capture_bedrock_failfast.py
  modified:
    - backend/pyproject.toml
    - backend/requirements.txt
    - backend/tests/conftest.py

key-decisions:
  - "Reused TriageSlice verbatim as the typed contract -- no new TriageResult model (Pitfall 3); extracted_fields stays deferred to Phase 2/JobSlice."
  - "triage_runner.py lives under backend/agents/ (not top-level), deliberately covered by the existing single-writer AST guard, per the plan's explicit override of RESEARCH.md's alternative suggestion."
  - "delegate=True set on .as_tool() for latency, but extract_triage_result's correctness never depends on delegate firing -- it reads the toolResult content block directly (belt-and-suspenders, source-verified against installed strands-agents==1.54.0)."
  - "Bedrock error mapping (map_bedrock_error) added in Task 5 only, kept out of the Task 3 tracer slice, so Task 5's TDD RED phase could genuinely fail before the 503 handling existed."

patterns-established:
  - "TDD gate sequence per behavior-adding task: test(...) RED commit (confirmed failing) then feat(...) GREEN commit, for both the agents-as-tools wiring and the Bedrock fail-fast handling."
  - "Package-legitimacy checkpoint (blocking-human) preceding any new third-party dependency install, pre-approved by the user for this run."

requirements-completed: [ORC-02, API-01, API-02]

coverage:
  - id: D1
    description: "POST /capture creates an EngagementRecord, runs triage via the DI seam, persists it, returns {engagement_id, verdict, score, reasoning}"
    requirement: "API-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_capture_endpoint.py#test_capture_creates_record_runs_triage_and_returns_verdict"
        status: pass
      - kind: unit
        ref: "backend/tests/test_capture_endpoint.py#test_capture_round_trips_via_get"
        status: pass
      - kind: unit
        ref: "backend/tests/test_capture_endpoint.py#test_capture_rejects_malformed_payload"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /engagements/{id} returns the persisted record with triage intact; unknown id returns 404"
    requirement: "API-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_engagements_endpoint.py#test_get_engagement_round_trips"
        status: pass
      - kind: unit
        ref: "backend/tests/test_engagements_endpoint.py#test_get_unknown_engagement_returns_404"
        status: pass
    human_judgment: false
  - id: D3
    description: "extract_triage_result reads the specialist's toolResult json block verbatim and ignores Supervisor prose; two distinct Agent instances construct offline with the specialist registered as a tool"
    requirement: "ORC-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_supervisor_wiring.py#test_extract_triage_result_reads_tool_result_block"
        status: pass
      - kind: unit
        ref: "backend/tests/test_supervisor_wiring.py#test_extract_triage_result_ignores_supervisor_prose"
        status: pass
      - kind: unit
        ref: "backend/tests/test_supervisor_wiring.py#test_extract_triage_result_raises_when_absent"
        status: pass
      - kind: unit
        ref: "backend/tests/test_supervisor_wiring.py#test_build_supervisor_registers_gig_triage_agent_tool"
        status: pass
      - kind: unit
        ref: "backend/tests/test_supervisor_wiring.py#test_two_distinct_agent_instances_exist"
        status: pass
    human_judgment: false
  - id: D4
    description: "/capture fails fast with a readable, credential-free 503 when the triage path raises a Bedrock error (ClientError / NoCredentialsError)"
    verification:
      - kind: unit
        ref: "backend/tests/test_capture_bedrock_failfast.py#test_capture_returns_503_on_bedrock_client_error"
        status: pass
      - kind: unit
        ref: "backend/tests/test_capture_bedrock_failfast.py#test_capture_maps_no_credentials"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live two-invocation trace against real Bedrock (Supervisor -> Gig Triage specialist, toolResult json block observed) -- manual-only per D-06, not gating this phase"
    verification: []
    human_judgment: true
    rationale: "Sandbox has only placeholder AWS credentials; this trace requires a human running with real Bedrock access, exactly as Phase 1's smoke tests documented."

duration: ~35min
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 1: Supervisor Wiring + /capture Endpoint Summary

**Real Strands Supervisor Agent routes to a Gig Triage specialist via agents-as-tools; FastAPI's `/capture` and `/engagements/{id}` run end-to-end offline against a deterministic placeholder, with the typed-channel merge and Bedrock fail-fast both proven by tests.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-02
- **Completed:** 2026-09-02
- **Tasks:** 5/5 completed
- **Files modified:** 13 (10 created, 3 modified)

## Accomplishments
- `POST /capture` (JobSlice in) -> deterministic triage -> `FileEngagementStore` persist -> verdict out, fully offline (API-01).
- `GET /engagements/{id}` read-through with 404 for unknown ids (API-02).
- Two distinct `strands.Agent` instances (Supervisor + Gig Triage specialist) construct offline; `extract_triage_result` reads the specialist's `toolResult` json content block directly out of `supervisor.messages`, proven (by test) to ignore the Supervisor's own re-authored prose (ORC-02/D-02).
- `/capture` fails fast with a readable, credential-free 503 (not a raw 500) when the (mocked) live Bedrock path raises `ClientError`/`NoCredentialsError`, reusing Phase 1's exact error-mapping taxonomy (T-03-02).
- Full backend test suite: **29 passed** (14 from Phase 1 + 15 new), `test_single_writer.py` stays green — only `api.py` imports the store.

## Task Commits

Each task was committed atomically:

1. **Task 1: Package-legitimacy checkpoint** - pre-approved by the user per the executor prompt; not re-halted.
2. **Task 2: Add + pin fastapi/uvicorn/httpx** - `2842add` (chore)
3. **Task 3: TRACER — /capture -> triage -> store -> verdict** - `ae4d86d` (feat)
4. **Task 4: Agents-as-tools typed channel (TDD)** - `7fd8608` (test, RED) -> `6f38bb9` (feat, GREEN)
5. **Task 5: Bedrock fail-fast 503 + 404 (TDD)** - `af0893c` (test, RED) -> `86862c5` (feat, GREEN)

_TDD tasks each have a confirmed-failing RED commit followed by a GREEN commit._

## Files Created/Modified
- `backend/tools/placeholder_triage.py` - deterministic budget-floor + red-flag-keyword `@tool` (D-03/D-04 Phase-2 stand-in)
- `backend/agents/gig_triage_agent.py` - `build_gig_triage_agent()`: real Agent, BedrockModel + `structured_output_model=TriageSlice`, construction-only (no network call)
- `backend/agents/supervisor.py` - `build_supervisor()` + `extract_triage_result()`: the ORC-02 typed-channel merge mechanism
- `backend/agents/triage_runner.py` - `TriageRunner` Protocol, deterministic + supervisor impls, `TRIAGE_BACKEND` env seam
- `backend/api.py` - FastAPI app, sole store writer; `/capture`, `/engagements/{id}`, `map_bedrock_error()`
- `backend/tests/conftest.py` - added `client` TestClient fixture (overrides `get_store` with tmp `file_store`)
- `backend/tests/test_capture_endpoint.py`, `test_engagements_endpoint.py`, `test_triage_runner.py`, `test_supervisor_wiring.py`, `test_capture_bedrock_failfast.py` - new test files covering API-01/API-02/ORC-02/D-03/T-03-01/T-03-02
- `backend/pyproject.toml`, `backend/requirements.txt` - added fastapi/uvicorn[standard]/httpx pins

## Decisions Made
- Kept `TriageSlice` as the sole typed contract (no new `TriageResult` model) per D-02/Pitfall 3.
- Placed `triage_runner.py` under `backend/agents/` exactly as the executor prompt directed (overriding RESEARCH.md's top-level suggestion), so the existing AST-based single-writer guard covers it.
- Deferred `map_bedrock_error`/503 handling entirely to Task 5 (not folded into Task 3's tracer) so its TDD RED phase produced a genuine failure rather than a pre-satisfied test.
- Used `delegate=True` on `.as_tool()` for the live path's latency win, but built `extract_triage_result` to never depend on it firing — it reads the `toolResult` content block directly, which is the verified, delegate-independent mechanism.

## Deviations from Plan

None - plan executed exactly as written. Task 1's package-legitimacy checkpoint was pre-approved per the executor's explicit instruction and was not re-halted.

## Issues Encountered
- Initial `test_capture_bedrock_failfast.py` overrides passed the raising closure directly as the `get_triage_runner` dependency override; FastAPI's dependency-injection machinery then tried to resolve the closure's own `job` parameter as a request input, producing a spurious 422 instead of exercising the failure path. Fixed by wrapping the raising closure in a zero-argument `lambda: ...` so FastAPI calls it with no injected parameters and only the *returned* callable receives `job` inside the route body (a corrected test, not a Rule 1-4 production deviation).

## User Setup Required
None - no external service configuration required for the automated/offline path. The manual live two-invocation trace (real Bedrock, `TRIAGE_BACKEND=supervisor`) remains a documented, optional, human-run verification per D-06 — see 03-01-PLAN.md's `user_setup` block for the env vars it needs (`BEDROCK_MODEL_ID`, `AWS_REGION`, `TRIAGE_BACKEND=supervisor`).

## Next Phase Readiness
- The `TriageRunner` seam (`backend/agents/triage_runner.py`) is stable and ready for Phase 2 to retarget the placeholder's body with the real `extract_job_fields`/`kill_switch_check`/`llm_scorecard` pipeline, without touching `api.py` or the Supervisor/specialist wiring.
- Phase 4 (Chrome extension) can POST directly against `/capture`'s existing `JobSlice` contract.
- No blockers. The only open item is the manual live-Bedrock two-invocation trace (D-06/ROADMAP success criterion 4), which is documented as human-run-only and does not gate this phase.

---
*Phase: 03-supervisor-wiring-capture-endpoint*
*Completed: 2026-09-02*
