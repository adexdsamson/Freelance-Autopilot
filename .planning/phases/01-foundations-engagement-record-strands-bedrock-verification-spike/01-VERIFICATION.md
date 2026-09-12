---
phase: 01-foundations-engagement-record-strands-bedrock-verification-spike
verified: 2026-09-01T11:46:55Z
status: human_needed
score: 3/4 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "A throwaway two-agent Strands smoke test shows a supervisor routing to a distinct specialist agent, with independent tool-call trace entries for each (ROADMAP Phase 1 SC3 / ORC-03)."
    test: "From backend/, with real AWS Bedrock credentials + model access exported (BEDROCK_MODEL_ID, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), run `python -m scripts.smoke_test_agents_as_tools`."
    expected: "main() completes without raising, prints 'PASS: agents-as-tools wiring confirmed, tool call recorded in trace', and the printed `supervisor.messages` / `result.metrics.tool_metrics` show a `toolUse` block naming `echo_specialist` — i.e. an independent, distinct specialist tool-call trace entry, not the supervisor answering inline."
    why_human: "Requires live AWS Bedrock credentials with model access, which this sandbox does not have (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are the literal placeholder 'proxy-injected', no AWS_REGION set). The offline pytest test (test_agents_as_tools_smoke.py) only proves the supervisor Agent constructs and echo_specialist is registered in tools=[...] — it makes no network call and therefore cannot observe an actual routing decision or a real tool-call trace entry. Manually running the script here reaches the real Bedrock call inside echo_specialist and raises an uncaught botocore.exceptions.ClientError (UnrecognizedClientException) before any trace is produced, confirming the trace-shape assertion (`toolUse` content blocks) has never been exercised against a real successful call."
---

# Phase 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike Verification Report

**Phase Goal:** The Engagement Record schema/store and the Strands multi-agent + Bedrock wiring are proven to work before any specialist agent is built on top of them.
**Verified:** 2026-09-01T11:46:55Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|---|---|---|
| 1 | A developer can create, save, and reload an Engagement Record by engagement_id through the store and get back an equivalent Pydantic object. | ✓ VERIFIED | `backend/store/file_engagement_store.py` `create`/`get`/`save`; `backend/tests/test_store.py::test_create_then_get_round_trips_equal_record` passes (`reloaded.model_dump() == record.model_dump()`). Ran `cd backend && python -m pytest tests/test_store.py -q` → 3 passed. |
| 2 | The store has exactly one caller path — no agent/tool writes to it directly. | ✓ VERIFIED | AST-based `backend/tests/test_single_writer.py` scans `backend/agents/` and `backend/tools/` for imports of `store*`. Confirmed the guard is live (not vacuous) by adding `backend/agents/_temp_violation.py` with `from store.engagement_store import EngagementStore`, re-running the test (it FAILED with "REC-03 violation..."), then removing the file (test PASSED again). `grep` across `backend/` confirms `FileEngagementStore`/`EngagementStore` are currently only referenced from `store/` itself and the test suite — no production caller yet exists, which is expected: Phase 1 has no FastAPI layer (that arrives in Phase 3), so this phase can only prove the negative guard, not that FastAPI is *the* caller. That stronger form of SC2 is out of scope until Phase 3 adds a caller at all. |
| 3 | A throwaway 2-agent Strands smoke test shows a supervisor routing to a distinct specialist with independent tool-call trace entries. | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | `backend/scripts/smoke_test_agents_as_tools.py` `build_supervisor()` wires `echo_specialist` (a real `@tool`-decorated function) into `Agent(tools=[echo_specialist])`. Offline test `test_agents_as_tools_smoke.py` (2 tests, both pass) proves construction succeeds and `"echo_specialist" in supervisor.tool_names` against the real installed `strands-agents==1.54.0` (verified: `pip show` / import reports version 1.54.0) — this closes off Pitfall 1 (AttributeError/API-shape risk). It does **not** exercise routing or a real trace: manually running `python -m scripts.smoke_test_agents_as_tools` in this sandbox reaches the real Bedrock call inside `echo_specialist` and raises an uncaught `botocore.exceptions.ClientError (UnrecognizedClientException)` before any `toolUse` trace block is produced. See `behavior_unverified_items` above. The plan's own design (D-07/D-08) explicitly scopes the live trace as manual, non-gating evidence — that is a sound and honestly-documented scoping decision, but it means the actual runtime claim in SC3 ("shows... routing... with independent tool-call trace entries") is unproven in this codebase/environment today. |
| 4 | A Bedrock connectivity smoke test calls Claude with an explicit pinned model id + region, OR fails fast with a readable, diagnosable error. | ✓ VERIFIED | `backend/scripts/smoke_test_bedrock_connectivity.py` constructs `BedrockModel(model_id=MODEL_ID, region_name=REGION)` explicitly (never a bare model-id string), calls the model once, and branches on typed `NoCredentialsError`/`ClientError`(by `Error.Code`)/`EndpointConnectionError` — never a bare `except Exception` first. I ran `cd backend && python -m scripts.smoke_test_bedrock_connectivity` directly (not just the pytest wrapper): it printed `FAIL: AWS credentials present but invalid/expired (UnrecognizedClientException). Check AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are current.` to stderr and exited 1 — a real, readable, diagnosable fail-fast, actually exercised, not just asserted by a test double. Confirmed the literal placeholder credential value `proxy-injected` (present in this sandbox's env) never appears in stdout/stderr. This satisfies the OR-clause of SC4 with genuine behavioral evidence, matching D-08's design. |

**Score:** 3/4 truths verified (1 present + wired, behavior not exercised — see item above)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `backend/models/engagement_record.py` | Pydantic v2 EngagementRecord + slices | ✓ VERIFIED | `JobSlice`/`TriageSlice`(`Literal["apply","skip"]`)/`ProposalSlice`/`ContractSlice`/`OpsSlice`/`EngagementRecord`, `engagement_id: UUID = Field(default_factory=uuid4)`, optional stage slices default `None`. |
| `backend/store/engagement_store.py` | Abstract store interface | ✓ VERIFIED | `EngagementStore(ABC)` with abstract `create`/`get`/`save`. |
| `backend/store/file_engagement_store.py` | Single concrete store impl | ✓ VERIFIED | Atomic write (`.json.tmp` + `os.replace`), `_path()` type-guards to `UUID` only (raises `TypeError` otherwise — defense in depth beyond Pydantic validation). |
| `backend/tests/test_engagement_record.py` | REC-01 tests | ✓ VERIFIED | 3 tests, all pass. |
| `backend/tests/test_store.py` | REC-02 tests | ✓ VERIFIED | 3 tests, all pass. |
| `backend/tests/test_single_writer.py` | REC-03 AST guard | ✓ VERIFIED | 1 test, passes; confirmed live via deliberate-violation experiment. |
| `backend/scripts/smoke_test_agents_as_tools.py` | Agents-as-tools spike | ✓ VERIFIED (construction only) | Present, substantive, real strands-agents API used; not behaviorally proven for routing/trace (see Truth 3). |
| `backend/scripts/smoke_test_bedrock_connectivity.py` | Bedrock fail-fast spike | ✓ VERIFIED | Present, substantive, ran and behaved exactly as documented. |
| `backend/tests/test_agents_as_tools_smoke.py` | Offline construction test | ✓ VERIFIED | 2 tests, both pass, no network call. |
| `backend/tests/test_bedrock_smoke.py` | Fail-fast/no-leak test | ✓ VERIFIED | 1 test, passes; independently confirmed by direct script run. |
| `backend/pyproject.toml` / `backend/requirements.txt` | Pinned deps, pytest config | ✓ VERIFIED | `strands-agents==1.54.0` (confirmed installed version matches), `pydantic>=2.13,<3`, `boto3>=1.43,<2`; `testpaths=["tests"]`, `pythonpath=["."]`. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `FileEngagementStore` | `EngagementStore` | subclass, single concrete impl | ✓ WIRED | Only one concrete class exists; only referenced from `store/` internals and tests (no production caller yet — expected pre-Phase-3). |
| `EngagementRecord.engagement_id` | `FileEngagementStore._path()` | UUID-typed field, `_path()` type-guarded | ✓ WIRED | `TriageSlice`/path-traversal test (`test_path_traversal_engagement_id_raises_validation_error`) passes; `_path()` raises `TypeError` on non-UUID input. |
| `smoke_test_bedrock_connectivity.main()` | `BedrockModel(model_id=, region_name=)` | explicit construction, never bare string | ✓ WIRED | Confirmed by source read + live run. |
| `agents/`, `tools/` | `store/*` | forbidden import (negative link) | ✓ VERIFIED ABSENT | Confirmed by AST scan + deliberate-violation experiment. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full backend suite green | `cd backend && python -m pytest -q` | `10 passed in 0.95s` | ✓ PASS |
| Single-writer guard is live, not vacuous | add violating import to `agents/_temp_violation.py`, rerun `pytest tests/test_single_writer.py -q`, remove, rerun | FAILED with "REC-03 violation..." then PASSED after removal | ✓ PASS |
| Bedrock fail-fast path, direct run (not test double) | `cd backend && python -m scripts.smoke_test_bedrock_connectivity` | `FAIL: AWS credentials present but invalid/expired (UnrecognizedClientException)...`, exit 1, no credential leak | ✓ PASS |
| Agents-as-tools live routing/trace | `cd backend && python -m scripts.smoke_test_agents_as_tools` | Uncaught `botocore.exceptions.ClientError (UnrecognizedClientException)` before any trace produced — expected in this credential-less sandbox per script design (D-07 spike deliberately doesn't catch exceptions) | ? SKIP — requires live AWS Bedrock creds, see behavior_unverified_items |
| No debt markers / stub patterns in phase files | grep TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER/"not yet implemented" across all `backend/**/*.py` | No matches | ✓ PASS |
| No leaked runtime data / bad commits | `git ls-files \| grep data/engagements`, `git status --short`, `git cat-file -t <3 commit hashes>` | No tracked data files, clean tree, all 3 commits present | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| REC-01 | Pydantic-typed Engagement Record with job/triage/proposal/contract/ops slices | ✓ SATISFIED | `models/engagement_record.py`, `test_engagement_record.py` (3/3 pass) |
| REC-02 | Engagement Record persisted per-engagement to a durable store behind an interface | ✓ SATISFIED | `store/file_engagement_store.py`, `test_store.py` (3/3 pass) |
| REC-03 | FastAPI is the sole writer that merges specialist output into the record | ⚠️ PARTIAL (scoped to Phase 1) | The negative guard (no agent/tool imports store) is proven and live-tested. The positive half — "FastAPI is the sole writer" — cannot be proven yet because no FastAPI layer exists in this phase; it is Phase 3's job to add the single caller and keep this guard green. Correctly scoped, not a Phase 1 gap, but Phase 3 must not skip re-checking this. |
| ORC-03 | Claude on Bedrock wired via Strands with explicit model id + region | ⚠️ PARTIAL | Construction/API-shape half fully proven offline against the real pinned SDK version; fail-fast half behaviorally proven by direct run; the live-completion / live-trace half is unexercised in this sandbox (behavior_unverified_items). |

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`, empty-implementation patterns, and "not yet implemented"/"coming soon" strings across all `backend/**/*.py` returned zero matches. `backend/agents/__init__.py` and `backend/tools/__init__.py` are intentionally empty placeholder packages — this is by design (the single-writer test's scan target, real specialists arrive in Phase 2) and is documented as such, not an unacknowledged stub.

### Human Verification Required

#### 1. Live agents-as-tools routing + tool-call trace (ROADMAP Phase 1 SC3, ORC-03)

**Test:** From `backend/`, with real AWS Bedrock credentials and model access exported (`BEDROCK_MODEL_ID`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), run `python -m scripts.smoke_test_agents_as_tools`.
**Expected:** The script prints `PASS: agents-as-tools wiring confirmed, tool call recorded in trace`; the printed `supervisor.messages` / `result.metrics.tool_metrics` show a distinct `echo_specialist` tool-call entry — proof the supervisor routed to the specialist rather than answering inline, and that the trace-shape assertion (`toolUse` content blocks) matches the real 1.54.0 output.
**Why human:** Requires live AWS Bedrock credentials with model access; this sandbox's credentials are the literal placeholder `proxy-injected` with no region set, so the real call fails before any trace is produced. This is the one part of the phase goal ("Strands multi-agent... wiring proven to work") that remains unproven by direct observation.

#### 2. Live Bedrock success-path completion (ROADMAP Phase 1 SC4, ORC-03) — optional, informational

**Test:** With real credentials, run `python -m scripts.smoke_test_bedrock_connectivity`.
**Expected:** Prints `PASS: Bedrock reachable in {REGION} with model {MODEL_ID}` and a real completion, return code 0.
**Why human:** Not required to close the gap for SC4 (the fail-fast branch already fully satisfies the OR-clause with real behavioral evidence in this verification), but confirms `BEDROCK_MODEL_ID` default (`us.anthropic.claude-sonnet-4-6`) is a real, accessible inference-profile id before Phase 2+ specialists depend on it.

### Gaps Summary

No structural gaps: all artifacts exist, are substantive, and are correctly wired; the full automated pytest suite (10/10) passes; the single-writer guard was proven live (not vacuous) via a deliberate violate/revert experiment; the Bedrock fail-fast path was independently re-run outside pytest and behaved exactly as documented, with no credential leak.

The one open item is SC3 (live 2-agent routing + trace), which is a genuine, environment-caused limitation (no real AWS Bedrock credentials in this sandbox) rather than a code defect — the offline substitute (construction + tool-registration check against the real pinned SDK) is a sound, meaningful proxy that closes off the API-shape/AttributeError risk (Pitfall 1), but it does not and cannot prove the actual routing/trace behavior the success criterion asserts. The plan and SUMMARY.md both document this honestly as a manual, later-environment step — that manual-only path is documented well (env var list, exact commands, expected output), but it has genuinely not been executed yet by anyone with real credentials. Recorded here as a human-verification item rather than a blocker, since forcing a FAIL would misrepresent a documented, intentional scope boundary as a coding defect. Phase 2/3 should not treat the live-trace shape assertion (`toolUse` blocks, `result.metrics.tool_metrics` string-matching) as fully validated until this item is closed.

---

_Verified: 2026-09-01T11:46:55Z_
_Verifier: Claude (gsd-verifier)_
