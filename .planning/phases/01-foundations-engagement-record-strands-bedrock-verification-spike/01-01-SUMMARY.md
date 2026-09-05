---
phase: 01-foundations-engagement-record-strands-bedrock-verification-spike
plan: 01
subsystem: backend-foundations
tags: [pydantic, strands-agents, bedrock, pytest, file-store, ast]

# Dependency graph
requires: []
provides:
  - Pydantic v2 EngagementRecord schema (JobSlice/TriageSlice/ProposalSlice/ContractSlice/OpsSlice) mirroring PRD §6.2
  - Abstract EngagementStore interface + single concrete FileEngagementStore (atomic JSON writes)
  - AST-based single-writer import-graph test enforcing REC-03/D-05
  - Verified strands-agents==1.54.0 agents-as-tools wiring shape (build_supervisor/echo_specialist)
  - Bedrock connectivity smoke test with fail-fast, non-secret-leaking diagnostics
affects: [phase-02-gig-triage-agent, phase-03-api-endpoints, phase-08-agentcore-swap]

actuals:
  tokens: 4600
  tasks: 3
  commits: 4

tech-stack:
  added: [strands-agents==1.54.0, pydantic>=2.13, boto3>=1.43, pytest]
  patterns:
    - "Optional-stage-slice Pydantic model (job required, triage/proposal/contract/ops Optional=None)"
    - "Abstract EngagementStore(ABC) + single concrete FileEngagementStore at one construction point"
    - "Atomic file write: tmp file + os.replace"
    - "AST-based (not regex) import-graph test for architectural boundary enforcement"
    - "Agents-as-tools: @tool-wrapped specialist Agent registered in supervisor's tools=[...]"
    - "Standalone throwaway smoke scripts under scripts/, excluded from api.py's import path"

key-files:
  created:
    - backend/pyproject.toml
    - backend/requirements.txt
    - backend/models/engagement_record.py
    - backend/store/engagement_store.py
    - backend/store/file_engagement_store.py
    - backend/tests/test_engagement_record.py
    - backend/tests/test_store.py
    - backend/tests/test_single_writer.py
    - backend/scripts/smoke_test_agents_as_tools.py
    - backend/scripts/smoke_test_bedrock_connectivity.py
    - backend/tests/test_agents_as_tools_smoke.py
    - backend/tests/test_bedrock_smoke.py
  modified:
    - .gitignore

key-decisions:
  - "Installed pinned deps (strands-agents==1.54.0, pydantic>=2.13,<3, boto3>=1.43,<2, pytest) via pip3 install --user so the plan's exact verify command (`cd backend && python -m pytest`) resolves them without needing venv activation"
  - "engagement_id typed as UUID with default_factory=uuid4 closes off path-traversal at the Pydantic model boundary before FileEngagementStore._path() ever sees it"
  - "Confirmed real strands-agents 1.54.0 attribute shapes (Agent.tool_names, Agent.tool_registry.registry, DecoratedFunctionTool.tool_name) via direct construction before writing the offline test, per RESEARCH.md Pitfall 1 guidance"

patterns-established:
  - "Pattern 1: Optional-stage-slice Engagement Record (Pydantic v2)"
  - "Pattern 2: Abstract store + single concrete implementation"
  - "Pattern 3: Agents-as-tools with @tool-wrapped specialist, construction separate from invocation"
  - "Pattern 4: Explicit BedrockModel(model_id=, region_name=) with typed exception branching"

requirements-completed: [REC-01, REC-02, REC-03, ORC-03]

coverage:
  - id: D1
    description: "EngagementRecord validates job-only with auto-assigned UUID engagement_id; rejects invalid triage verdict and path-traversal engagement_id strings"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_engagement_record.py#test_job_only_record_validates_with_uuid_engagement_id"
        status: pass
      - kind: unit
        ref: "backend/tests/test_engagement_record.py#test_invalid_triage_verdict_raises_validation_error"
        status: pass
      - kind: unit
        ref: "backend/tests/test_engagement_record.py#test_path_traversal_engagement_id_raises_validation_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "FileEngagementStore create/get/save round-trips a record through the store seam, returns None for unknown ids, and writes atomically (no leftover .tmp file)"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "backend/tests/test_store.py#test_create_then_get_round_trips_equal_record"
        status: pass
      - kind: unit
        ref: "backend/tests/test_store.py#test_get_unknown_id_returns_none"
        status: pass
      - kind: unit
        ref: "backend/tests/test_store.py#test_save_is_atomic_no_leftover_tmp_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "No module under backend/agents/ or backend/tools/ imports the store (AST-based import-graph guard), verified live against a deliberate temp violation"
    requirement: "REC-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_single_writer.py#test_no_agent_or_tool_module_imports_store"
        status: pass
    human_judgment: false
  - id: D4
    description: "Agents-as-tools wiring constructs against strands-agents==1.54.0 (build_supervisor returns an Agent with echo_specialist registered), verified offline with no network call"
    requirement: "ORC-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_agents_as_tools_smoke.py#test_build_supervisor_constructs_without_raising_and_returns_agent"
        status: pass
      - kind: unit
        ref: "backend/tests/test_agents_as_tools_smoke.py#test_echo_specialist_tool_is_registered_on_supervisor"
        status: pass
    human_judgment: false
  - id: D5
    description: "Bedrock connectivity smoke test returns 0/1, never raises, and never leaks the sandbox's placeholder credential literal; this sandbox exercises the designed fail-fast path (UnrecognizedClientException, exit 1)"
    requirement: "ORC-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_bedrock_smoke.py#test_main_returns_int_in_0_or_1_and_never_raises_and_never_leaks_credentials"
        status: pass
      - kind: manual_procedural
        ref: "cd backend && python -m scripts.smoke_test_bedrock_connectivity"
        status: pass
    human_judgment: true
    rationale: "A live, credential-backed Bedrock completion (the success-path half of ORC-03) cannot be exercised in this sandbox (placeholder AWS credentials, no AWS_REGION) — a human with real AWS Bedrock access must run the script once against a live account to confirm the success branch and capture a distinct specialist tool-call trace, per the plan's Manual-Only Verifications."

duration: 45min
completed: 2026-09-01
status: complete
---

# Phase 1 Plan 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike Summary

**Pydantic v2 EngagementRecord + atomic-write FileEngagementStore behind a single-writer-enforced interface, plus a verified strands-agents==1.54.0 agents-as-tools wiring and a fail-fast, non-leaking Bedrock connectivity smoke test.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-01T11:00Z (approx.)
- **Completed:** 2026-09-01T11:45Z (approx.)
- **Tasks:** 3
- **Files modified:** 19 (18 created, 1 edited)

## Accomplishments
- `EngagementRecord` Pydantic v2 model mirroring PRD §6.2 exactly (`JobSlice` required, `TriageSlice`/`ProposalSlice`/`ContractSlice`/`OpsSlice` optional slices), with `engagement_id: UUID` auto-assigned via `default_factory=uuid4` — closes off path traversal structurally, not just by convention.
- `EngagementStore(ABC)` + the single concrete `FileEngagementStore`, writing one JSON file per `engagement_id` under a configurable `base_dir`, using Pydantic v2 `model_dump_json`/`model_validate_json` and an atomic temp-file + `os.replace` write.
- AST-based (not regex) single-writer test (`test_single_writer.py`) that scans `backend/agents/` and `backend/tools/` for any import of the store module — verified live by deliberately adding then removing a violating import.
- Verified the real `strands-agents==1.54.0` API surface by direct construction (`Agent.tool_names`, `Agent.tool_registry.registry`, `DecoratedFunctionTool.tool_name`) before writing assertions, per RESEARCH.md's Pitfall 1 guidance — the offline `test_agents_as_tools_smoke.py` suite needs no network call or AWS credentials.
- `smoke_test_bedrock_connectivity.py` constructs an explicit `BedrockModel(model_id=, region_name=)`, calls it once, and branches on `NoCredentialsError`/`ClientError` (by `Error.Code`)/`EndpointConnectionError` — confirmed in this sandbox to fail fast with a readable `UnrecognizedClientException` diagnosis (exit 1) and never echo the placeholder credential literal `"proxy-injected"`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold backend + Engagement Record model + file store** - `05436c1` (feat)
2. **Task 2: Single-writer import-graph test (REC-03)** - `324fc49` (feat)
3. **Task 3: Strands agents-as-tools + Bedrock fail-fast smoke spike (ORC-03)** - `8b222fd` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `backend/pyproject.toml` - pytest config (`testpaths=["tests"]`, `pythonpath=["."]`) + pinned project deps
- `backend/requirements.txt` - pinned dependency list matching pyproject
- `backend/models/engagement_record.py` - `JobSlice`/`TriageSlice`/`ProposalSlice`/`ContractSlice`/`OpsSlice`/`EngagementRecord`
- `backend/store/engagement_store.py` - abstract `EngagementStore(ABC)` (`create`/`get`/`save`)
- `backend/store/file_engagement_store.py` - concrete `FileEngagementStore` with atomic JSON writes
- `backend/agents/__init__.py`, `backend/tools/__init__.py` - empty placeholder packages, single-writer scan targets
- `backend/tests/conftest.py` - `file_store` fixture bound to pytest's `tmp_path`
- `backend/tests/test_engagement_record.py` - REC-01 tests
- `backend/tests/test_store.py` - REC-02 tests
- `backend/tests/test_single_writer.py` - REC-03 AST import-graph test
- `backend/scripts/smoke_test_agents_as_tools.py` - throwaway agents-as-tools spike (D-07)
- `backend/scripts/smoke_test_bedrock_connectivity.py` - throwaway Bedrock fail-fast spike (D-06/D-08)
- `backend/tests/test_agents_as_tools_smoke.py` - offline construction/registration assertions
- `backend/tests/test_bedrock_smoke.py` - fail-fast/no-leak assertions
- `.gitignore` - added `backend/data/` so runtime Engagement Record JSON is never committed

## Decisions Made
- Installed the pinned dependencies via `pip3 install --user` (after a `python -m venv` attempt proved unnecessary for the plan's exact verify command) so `cd backend && python -m pytest` — the literal command specified in every task's `<verify>` — resolves `strands`, `pydantic`, and `boto3` without requiring venv activation. A throwaway `backend/.venv` was created during exploration and removed once this was confirmed; it is also covered by the existing `.venv/` gitignore rule.
- `FileEngagementStore._path()` additionally raises `TypeError` if ever called with a non-`UUID` (defense in depth beyond the Pydantic-validated caller boundary) — not explicitly required by the plan's acceptance criteria but directly implements the T-01-01 mitigation intent (`_path()` never interpolates a raw string).
- Wrote the agents-as-tools offline test against the real, directly-observed `strands-agents==1.54.0` attribute shapes (`Agent.tool_names`, `DecoratedFunctionTool.tool_name`) rather than guessing, per RESEARCH.md Pitfall 1's explicit instruction to verify before asserting.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] System-wide pip install blocked by Debian-managed package conflict**
- **Found during:** Task 1 (dependency install)
- **Issue:** `pip3 install <pinned deps>` at the system level failed with `Cannot uninstall PyJWT 2.7.0, RECORD file not found. Hint: The package was installed by debian.`
- **Fix:** Used `pip3 install --user <pinned deps>` instead, which installs into user site-packages without touching the Debian-managed system packages; confirmed `python -m pytest` (the plan's literal verify command) picks these up correctly.
- **Files modified:** none (environment-only)
- **Verification:** `cd backend && python -m pytest -q` passes all 10 tests using the plain `python` interpreter.
- **Committed in:** n/a (no source change; environment setup only)

---

**Total deviations:** 1 auto-fixed (1 blocking, environment-only)
**Impact on plan:** No scope creep — purely an installation-path workaround so the plan's own verify commands run as literally specified.

## Issues Encountered
- Manually running `python -m scripts.smoke_test_agents_as_tools` in this sandbox (as opposed to the pytest-wrapped offline test) raises an uncaught `botocore.exceptions.ClientError` (`UnrecognizedClientException`) when `main()` reaches the real Bedrock call inside `echo_specialist`'s internal specialist `Agent`. This is expected and non-gating: the script is a throwaway spike whose `main()` deliberately does not catch exceptions (unlike `smoke_test_bedrock_connectivity.py`, which is required to fail fast), and the automated pytest suite only exercises `build_supervisor()` offline, which never reaches this code path. Recorded here as the manual evidence the plan's `<verification>` section calls for.
- Because this sandbox has no real Bedrock access, the exact live shape of `supervisor.messages` tool-call content blocks (`toolUse` key) and `result.metrics.tool_metrics` after a *successful* call could not be independently confirmed — only construction-time attributes (`Agent.tool_names`, `tool_registry.registry`, `DecoratedFunctionTool.tool_name`) were directly verified. The `main()` trace assertion follows the Bedrock Converse API's documented camelCase content-block naming (RESEARCH.md Pattern 3) but should be re-verified against a real successful call before being relied on in the demo recording.

## Known Stubs

None that block this plan's goal. The following are explicitly out-of-scope placeholders by design, not gaps:
- `backend/agents/__init__.py` and `backend/tools/__init__.py` are intentionally empty (docstring-only) placeholder packages — real specialist code arrives in Phase 2+, and this phase's single-writer test specifically depends on them being empty today.
- `backend/scripts/smoke_test_*.py` are explicitly throwaway spikes (D-07/D-08), never imported by future `api.py` — not stubs to be "completed," they are complete as designed.

## User Setup Required

**External services require manual configuration for the live-credential success path only (non-gating for this phase).** Per the plan's `user_setup` frontmatter:
- `BEDROCK_MODEL_ID` — confirm the exact inference-profile Claude model id against the AWS account's Bedrock "Model access" page (code default is a placeholder: `us.anthropic.claude-sonnet-4-6`).
- `AWS_REGION` — the region where Bedrock model access was granted.
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — real AWS credentials with `bedrock:InvokeModel` permission.

None of these are required for this phase to be considered done — REC-01/02/03 have zero AWS dependency, and ORC-03's fail-fast path (this sandbox's actual condition) is itself the designed PASS per D-08.

## Next Phase Readiness
- The `EngagementStore` interface and `FileEngagementStore` are ready for Phase 2's Gig Triage Agent to consume (read-only) and for Phase 3's FastAPI layer to become the sole writer.
- The single-writer AST test is live and will fail the moment any Phase 2+ agent/tool module imports `store` directly — this is the intended regression guard.
- The agents-as-tools wiring shape (`@tool`-wrapped specialist, `build_supervisor()`-style factory) is proven against the pinned SDK and ready to be reused for the real Gig Triage Agent in Phase 2.
- Blocker/concern: a live, credential-backed Bedrock completion and a real specialist tool-call trace have not been captured in this sandbox — someone with real AWS Bedrock access should run both smoke scripts once before the demo recording to confirm the success path and the exact `agent.messages`/`tool_metrics` shape.

---
*Phase: 01-foundations-engagement-record-strands-bedrock-verification-spike*
*Completed: 2026-09-01*

## Self-Check: PASSED

All 12 claimed files verified present on disk; all 3 task commit hashes (`05436c1`, `324fc49`, `8b222fd`) verified present in git history.
