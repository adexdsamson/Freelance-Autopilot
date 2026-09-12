---
phase: 03-supervisor-wiring-capture-endpoint
verified: 2026-09-02T00:00:00Z
status: human_needed
score: 3/4 must-haves verified
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Two distinct Agent instances (Supervisor + Gig Triage) invoke separately at runtime (roadmap success criterion 4) — a live trace showing two Agent invocations, not one flat call."
    test: "With real AWS/Bedrock credentials, set TRIAGE_BACKEND=supervisor, POST /capture, and inspect the resulting supervisor.messages / logs for two distinct Agent invocation traces (Supervisor's model call, then the gig_triage_agent tool's own model call) plus the toolResult {\"json\": ...} content block."
    expected: "Two separate Agent.__call__/stream_async invocations appear in the trace (one for the Supervisor, one for the gig_triage_agent specialist), and the specialist's toolResult json block is present in supervisor.messages."
    why_human: "Requires live Bedrock credentials to actually invoke both Agents; the sandbox only has placeholder AWS credentials (confirmed in SUMMARY.md, D5 rationale). No automated test in the suite invokes either Agent — both test_supervisor_wiring.py tests are construction-only or pure-function tests over synthetic messages."
human_verification:
  - test: "With real AWS/Bedrock credentials, set TRIAGE_BACKEND=supervisor, POST /capture, and inspect the resulting trace/log for two distinct Agent invocations."
    expected: "Supervisor invocation followed by a distinct gig_triage_agent invocation are both visible in the trace, and the specialist's structured_output toolResult json block is what extract_triage_result reads."
    why_human: "No automated coverage exists or can exist offline; this is explicitly scoped as manual-only in the plan (D-06) and the SUMMARY (D5, human_judgment: true)."
---

# Phase 3: Supervisor Wiring + `/capture` Endpoint Verification Report

**Phase Goal:** A real Strands Supervisor Agent orchestrates the Gig Triage Agent via agents-as-tools, and Stage 1 is reachable end-to-end through FastAPI.
**Verified:** 2026-09-02
**Status:** human_needed
**Re-verification:** No — initial verification

## Test Suite (actually run, not trusted from SUMMARY)

```
cd backend && python -m pytest -q
29 passed, 1 warning in 1.51s
```

Collected test list confirms 14 Phase-1 tests (`test_engagement_record.py`, `test_store.py`,
`test_single_writer.py`, `test_agents_as_tools_smoke.py`, `test_bedrock_smoke.py`) plus 15 new
Phase-3 tests (`test_capture_endpoint.py` x3, `test_engagements_endpoint.py` x2,
`test_supervisor_wiring.py` x5, `test_triage_runner.py` x3, `test_capture_bedrock_failfast.py`
x2) — matches the SUMMARY's "29 passed (14 + 15)" claim exactly, independently reproduced.

## Goal Achievement

### Observable Truths (ROADMAP success criteria, verbatim)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `POST /capture` with a structured job payload creates a new Engagement Record, runs triage through the Supervisor, and returns the verdict. | ✓ VERIFIED | `backend/api.py:76-94` — `capture()` builds `EngagementRecord(job=job)`, calls `triage_runner(job)` (DI seam, default = deterministic placeholder per D-03), `store.create(record)`, returns `CaptureResponse`. Tested live: `tests/test_capture_endpoint.py::test_capture_creates_record_runs_triage_and_returns_verdict` — PASSED. Caveat: on the *default* offline path, triage runs through the deterministic placeholder, not a live Supervisor Bedrock call — this is the explicitly-scoped, documented substitute per D-03/D-06(b), not a hidden gap. |
| 2 | `GET /engagements/{id}` returns the persisted record with the triage slice populated exactly as the specialist produced it; unknown id -> 404. | ✓ VERIFIED | `backend/api.py:97-105`. `tests/test_engagements_endpoint.py::test_get_engagement_round_trips` and `::test_get_unknown_engagement_returns_404` — both PASSED. `tests/test_capture_endpoint.py::test_capture_round_trips_via_get` cross-checks GET body's `triage.{verdict,score,reasoning}` equal the original POST response fields byte-for-byte. |
| 3 | The Gig Triage typed JSON reaches the record unmodified — the Supervisor's model does not re-author it before FastAPI merges it. | ✓ VERIFIED | `backend/agents/supervisor.py:46-60` `extract_triage_result()` walks `supervisor.messages` for a `toolResult` content block containing a `"json"` key and validates it into `TriageSlice` — it never inspects assistant `text` blocks. Source-verified against the installed `strands-agents==1.54.0` package (`/root/.local/lib/python3.11/site-packages/strands/agent/_agent_as_tool.py:256-263`): when the wrapped specialist Agent has `structured_output_model` set, `_AgentAsTool.stream()` emits `{"json": result.structured_output.model_dump(...)}` **before** the `delegate` branch is even reached — confirming `extract_triage_result`'s correctness does not depend on `delegate` firing, exactly as the code's docstring and SUMMARY claim. `tests/test_supervisor_wiring.py::test_extract_triage_result_ignores_supervisor_prose` constructs a synthetic message list where the assistant's own prose text asserts the OPPOSITE verdict from the toolResult json, and asserts `extract_triage_result` returns the toolResult's verdict — PASSED (re-ran individually to confirm, not just trusted from the full-suite run). |
| 4 | Trace/log inspection of one `/capture` call shows two distinct Agent invocations (Supervisor and Gig Triage), not one flat call. | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Two distinct `Agent` **instances** genuinely construct offline and the specialist is registered as a tool on the Supervisor — `backend/agents/supervisor.py:26-27` (`gig_triage_agent = build_gig_triage_agent()`; `triage_tool = gig_triage_agent.as_tool(...)`), confirmed by `tests/test_supervisor_wiring.py::test_two_distinct_agent_instances_exist` (asserts `supervisor is not gig_triage_agent`) and `::test_build_supervisor_registers_gig_triage_agent_tool` (asserts `"gig_triage_agent" in supervisor.tool_names`) — both PASSED. **However**, this only proves two distinct *objects* exist at construction time; it does not exercise a live invocation trace showing two distinct Agent *invocations* at runtime, because that requires real Bedrock credentials the sandbox does not have. No automated test in the suite invokes either Agent (`build_supervisor()`/`build_gig_triage_agent()` are called but the returned `Agent` objects are never `__call__`'d in any test). This is honestly disclosed, not silently skipped: SUMMARY.md's `coverage` block explicitly marks this item (`D5`) `human_judgment: true` with `verification: []` and a stated rationale ("Sandbox has only placeholder AWS credentials"), and the PLAN's own must-haves already scope truth #4 as "the live two-invocation trace is a documented manual verification" — so this is a pre-planned, disclosed gap in automated coverage, not a fabricated PASS claim. Routed to human verification below; does not count toward the verified score. |

**Score:** 3/4 truths verified (1 present + wired, behavior/trace not exercised)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/api.py` | FastAPI app, sole store writer, `/capture` + `/engagements/{id}` | ✓ VERIFIED | Exists, substantive, wired; only module importing `store.*` (confirmed by AST-based `test_single_writer.py`, PASSED). |
| `backend/agents/supervisor.py` | `build_supervisor()`, `extract_triage_result()` | ✓ VERIFIED | Both present, source-verified against installed strands package, exercised by 5 passing tests. |
| `backend/agents/gig_triage_agent.py` | `build_gig_triage_agent()` | ✓ VERIFIED | Real `Agent` with `BedrockModel` + `structured_output_model=TriageSlice`; construction performs no network call (confirmed — offline construction tests pass without AWS creds). |
| `backend/agents/triage_runner.py` | `TriageRunner` Protocol + env-flag seam | ✓ VERIFIED | `TRIAGE_BACKEND` env var selects `_deterministic_triage_runner` (default) vs `_supervisor_triage_runner`; both branches tested (`test_triage_runner.py`, 3 tests PASSED). Neither imports the store. |
| `backend/tools/placeholder_triage.py` | Deterministic budget/keyword `@tool` | ✓ VERIFIED | Pure-Python, no LLM/randomness; used directly (offline path) and registered as a tool (live path) — one source of truth, matching the plan. |
| 5 new test files | API-01/API-02/ORC-02/D-03/T-03-01/T-03-02 coverage | ✓ VERIFIED | All exist, all substantive (no empty stubs), all pass individually and in the full suite. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `api.py` `POST /capture` | `agents/triage_runner.get_triage_runner()` | `Depends(get_triage_runner)` | ✓ WIRED | Confirmed by reading `api.py:80` and by `test_capture_endpoint.py`/`test_capture_bedrock_failfast.py` (which override this exact dependency object, proving the wiring is the real injected callable, not a decoupled duplicate). |
| `api.py` | `store.create(record)` | direct call after triage merge | ✓ WIRED | `api.py:88`; only api.py imports the store module (AST-verified). |
| `supervisor.as_tool(gig_triage_agent, delegate=True)` | `extract_triage_result` | `toolResult` `{"json":...}` content block in `supervisor.messages` | ✓ WIRED (source-verified) | Confirmed against `strands/agent/_agent_as_tool.py:256-263`: `structured_output` branch fires before `delegate` branch, populating exactly the shape `extract_triage_result` parses. |
| `TRIAGE_BACKEND` env flag | `get_triage_runner()` | `os.environ.get("TRIAGE_BACKEND", "placeholder")` | ✓ WIRED | Both branches tested with `monkeypatch.setenv`/`delenv`. |
| `agents/` + `tools/` modules | store | must NOT import | ✓ ENFORCED | `test_single_writer.py`'s AST-based scan (not a regex) — PASSED; independently confirmed no `store` import appears in any of the 5 new agent/tool files by direct read. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `cd backend && python -m pytest -q` | `29 passed, 1 warning in 1.51s` | ✓ PASS |
| Prose-vs-toolResult precedence | `pytest tests/test_supervisor_wiring.py::test_extract_triage_result_ignores_supervisor_prose -v` | PASSED (re-run individually, not just trusted from full run) | ✓ PASS |
| Bedrock fail-fast, no credential leak | `pytest tests/test_capture_bedrock_failfast.py -v` | Both tests PASSED; asserted absence of `"proxy-injected"` / raw AWS Message string | ✓ PASS |
| Package pins match approved Task-1 gate | `python -c "import fastapi, httpx, uvicorn; print(...)"` | `0.141.1 0.28.1 0.52.4` — within `>=0.141,<0.142` / `>=0.52,<0.53` pins in `pyproject.toml`/`requirements.txt` | ✓ PASS |
| Two Agent invocations at runtime (criterion 4) | requires live Bedrock creds | not run (sandbox has no real AWS creds) | ? SKIP -> routed to human verification |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|--------------|------------|-------------|--------|----------|
| ORC-02 | 03-01-PLAN.md | Specialist typed JSON merged verbatim, no re-authoring | ✓ SATISFIED | `test_supervisor_wiring.py` (5 tests, source-verified mechanism) |
| API-01 | 03-01-PLAN.md | `POST /capture` end-to-end | ✓ SATISFIED | `test_capture_endpoint.py`, `test_capture_bedrock_failfast.py` |
| API-02 | 03-01-PLAN.md | `GET /engagements/{id}` round-trip + 404 | ✓ SATISFIED | `test_engagements_endpoint.py` |

No orphaned requirements: `REQUIREMENTS.md` maps only ORC-02/API-01/API-02 to Phase 3, and all three appear in the plan's `requirements` frontmatter. (Note: `REQUIREMENTS.md`'s own checklist still shows these three as unchecked/"Pending" — a doc-tracking staleness issue, not a code gap; flagged as informational only, not a verification blocker.)

### Anti-Patterns Found

None. Grepped all 10 phase-3 files for `TBD|FIXME|XXX|TODO|HACK`, hardcoded empty returns, and console.log-only stubs — zero hits. Every "placeholder" reference in the code is the deliberate, clearly-documented Phase-2 stand-in (D-03/D-04) explicitly called for by the plan (Phase 2 does not exist yet in this repo — confirmed by `ls .planning/phases/`), not a hidden incompleteness. The placeholder logic itself is a real, deterministic, testable rule (budget floor + keyword scan), not a stub returning empty/null data.

### Human Verification Required

#### 1. Live two-invocation trace (ROADMAP success criterion 4)

**Test:** With real AWS/Bedrock credentials configured, set `TRIAGE_BACKEND=supervisor`, `BEDROCK_MODEL_ID`, `AWS_REGION`, then `POST /capture` with a structured job payload and inspect the resulting Supervisor's `messages`/logs (or add temporary tracing).
**Expected:** Two distinct Agent invocations are visible — one for the Supervisor's own model turn, one for the `gig_triage_agent` specialist's model turn — and the specialist's `structured_output` `toolResult` `{"json": {...}}` content block is present in `supervisor.messages`, matching what `extract_triage_result` reads.
**Why human:** No AWS credentials exist in this sandbox (only placeholder/proxy-injected values per Phase 1's precedent); this is a live external-service call that cannot be exercised offline. This is not a gap introduced by sloppy execution — the plan (`03-01-PLAN.md`, must_haves truth #4, D-06) and the SUMMARY (`D5`, `human_judgment: true`) both pre-scoped and disclosed this as manual-only. Automated coverage stops at "two distinct Agent objects construct and one is registered as a tool of the other" (verified) and does not extend to "two distinct Agent invocations occur at runtime" (unverified by any test).

### Gaps Summary

No FAILED truths, no missing/stub artifacts, no broken key links, no unresolved debt markers. The
single open item is criterion 4's live-invocation trace, which was never claimed as automated by
either the PLAN or the SUMMARY — it is disclosed, pre-scoped, human-verification-only work,
correctly routed here rather than silently passed. Everything else the phase set out to build
(real Supervisor+specialist Agent wiring, the typed-channel merge mechanism, `/capture`/`GET
/engagements/{id}`, sole-writer enforcement, credential-safe 503 fail-fast) is genuinely present,
substantive, wired, and independently reproduced by an actual pytest run in this session (not
trusted from SUMMARY.md).

**Recommendation:** Proceed to the next phase. This is not a blocker for Phase 4/5/6 — the
`TriageRunner` seam and typed-channel mechanism are real and independent of whether the live
Bedrock trace has been human-verified yet. Before demo recording, a human should run the manual
trace once with real Bedrock credentials to close this item.

---

*Verified: 2026-09-02*
*Verifier: Claude (gsd-verifier)*
