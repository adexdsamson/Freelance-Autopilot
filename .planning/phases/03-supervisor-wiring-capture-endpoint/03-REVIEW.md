---
phase: 03-supervisor-wiring-capture-endpoint
reviewed: 2026-09-02T22:16:12Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - backend/api.py
  - backend/agents/supervisor.py
  - backend/agents/gig_triage_agent.py
  - backend/agents/triage_runner.py
  - backend/tools/placeholder_triage.py
  - backend/tests/conftest.py
  - backend/tests/test_capture_bedrock_failfast.py
  - backend/tests/test_capture_endpoint.py
  - backend/tests/test_engagements_endpoint.py
  - backend/tests/test_supervisor_wiring.py
  - backend/tests/test_triage_runner.py
  - backend/pyproject.toml
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-09-02T22:16:12Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Supervisor wiring + `/capture` endpoint code added on
`gsd/phase-03-supervisor-wiring-capture-endpoint`. The happy-path plumbing is
solid: `/capture` creates and persists an `EngagementRecord`, the typed
`TriageSlice` merge in `extract_triage_result` is genuinely read from the
specialist's `toolResult` block (verified directly against the installed
`strands-agents==1.54.0` source — `_AgentAsTool.stream()` really does emit
`result.structured_output` as a `json` toolResult content block before any
`delegate` re-authoring branch runs, confirming the ORC-02 claim in the
docstring), `engagement_id` is UUID-typed end-to-end (confirmed 422 on a
malformed UUID path param, closing path traversal), and 422/404 status codes
work as advertised. The sole-writer guard (`test_single_writer.py`) passes
and no other agent/tool module imports the store.

However, two BLOCKER-level gaps were found by direct testing (not just
reading): (1) `map_bedrock_error`'s exception taxonomy is a strict subset of
the taxonomy it claims to mirror (`smoke_test_bedrock_connectivity.py`) —
`ModelThrottledException` and `ContextWindowOverflowException`, both
strands-specific `Exception` subclasses (not `BotoCoreError`), are real,
documented, expected Bedrock failure modes that fall straight through
`/capture`'s except clause and surface as a raw unhandled 500 instead of the
required readable 503; I reproduced this. (2) `extract_triage_result` does
not actually fail safe on malformed `toolResult` content — it raises an
undocumented `TypeError` instead of the advertised `RuntimeError` when an
inner content block isn't a dict; I reproduced this too. Additionally, every
single automated test in this phase exercises `placeholder_kill_switch_check`
with the same `budget=500.0` / no-red-flag-keyword input, so the "skip"
verdict paths of the one deterministic rule every test in the suite (and the
whole offline demo) depends on have zero test coverage — the rule itself is
correct (verified manually), but that correctness is unproven by the suite.

## Critical Issues

### CR-01: Bedrock exception taxonomy in `map_bedrock_error` does not match its own documented source of truth — real failure modes crash as raw 500s

**File:** `backend/api.py:52-73` (and the `except` clause at `backend/api.py:85`)
**Issue:**
`map_bedrock_error`'s docstring states: "Mirrors backend/scripts/smoke_test_bedrock_connectivity.py's taxonomy... `BotoCoreError` catch-all, final `Exception` safety net". It does not. `capture()`'s except clause only catches `(NoCredentialsError, ClientError, BotoCoreError)`. Two exception types that Phase 1's own smoke test (`backend/scripts/smoke_test_bedrock_connectivity.py:34-37,100-110`) explicitly branches on — `strands.types.exceptions.ModelThrottledException` and `strands.types.exceptions.ContextWindowOverflowException` — are **not** `BotoCoreError` subclasses (confirmed: `ModelThrottledException.__mro__` = `(ModelThrottledException, Exception, BaseException, object)`), so they are not caught. There is also no final `except Exception` safety net, unlike the script it claims to mirror.

I reproduced this directly:
```python
from fastapi.testclient import TestClient
from api import app, get_triage_runner
from strands.types.exceptions import ModelThrottledException

app.dependency_overrides[get_triage_runner] = lambda: (lambda job: (_ for _ in ()).throw(ModelThrottledException("x")))
with TestClient(app, raise_server_exceptions=False) as c:
    r = c.post("/capture", json={"title": "t", "description": "d", "budget": 500.0})
    print(r.status_code, r.text)  # -> 500 "Internal Server Error"
```
This is reachable only via the live `TRIAGE_BACKEND=supervisor` path (not exercised in CI per D-06), but it is a real, common Bedrock failure mode (throttling) that is plausible to hit during an actual demo run against live Bedrock, and directly contradicts T-03-02/D-06's "fail fast, readable 503" requirement that this exact code claims to satisfy.

**Fix:**
```python
from strands.types.exceptions import ContextWindowOverflowException, ModelThrottledException

def map_bedrock_error(exc: Exception) -> BedrockUnavailableError:
    if isinstance(exc, NoCredentialsError):
        return BedrockUnavailableError("no AWS credentials found for Bedrock.")
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        return BedrockUnavailableError(f"Bedrock ClientError [{code}] — see the Bedrock console.")
    if isinstance(exc, ModelThrottledException):
        return BedrockUnavailableError("Bedrock throttled the model invocation.")
    if isinstance(exc, ContextWindowOverflowException):
        return BedrockUnavailableError("prompt exceeded the model's context window.")
    if isinstance(exc, BotoCoreError):
        return BedrockUnavailableError(f"AWS SDK error ({type(exc).__name__}) talking to Bedrock.")
    return BedrockUnavailableError(f"unexpected error contacting Bedrock ({type(exc).__name__}).")

# and in capture():
except (NoCredentialsError, ClientError, BotoCoreError,
        ModelThrottledException, ContextWindowOverflowException) as exc:
    ...
```
Consider also a final broad-exception fallback specifically around the `triage_runner(job)` call (not the whole handler) so any future strands exception type added upstream degrades to a 503 instead of a raw 500, matching the "must never crash" precedent set by Phase 1's own script.

### CR-02: `extract_triage_result` does not fail safe on malformed `toolResult` content — raises an undocumented `TypeError` instead of `RuntimeError`

**File:** `backend/agents/supervisor.py:46-60`
**Issue:** The function guards against the outer `content` block not being a dict (`if not isinstance(block, dict) or "toolResult" not in block: continue`), but never validates that entries inside `block["toolResult"]["content"]` are dicts before doing `"json" in content_block` (membership) followed by `content_block["json"]` (indexing). If an entry is a non-dict (e.g. a bare string), `"json" in content_block` becomes a substring-containment check (which can spuriously match), and then `content_block["json"]` raises `TypeError: string indices must be integers, not 'str'` — an unhandled crash, not the advertised graceful "fail safe" / `RuntimeError("gig_triage_agent tool result not found...")`.

Reproduced directly:
```python
from agents.supervisor import extract_triage_result
messages = [{"role": "assistant", "content": [{"toolResult": {
    "toolUseId": "x", "status": "success", "content": ["not-a-dict-with-json-substring"]
}}]}]
extract_triage_result(messages)
# -> TypeError: string indices must be integers, not 'str'
```
This `TypeError` is also not caught by `capture()`'s except clause (CR-01), so a malformed supervisor trace on the live path would surface as a raw 500, not a 503, compounding CR-01.
**Fix:**
```python
for content_block in block["toolResult"].get("content", []):
    if isinstance(content_block, dict) and "json" in content_block:
        return TriageSlice.model_validate(content_block["json"])
```

## Warnings

### WR-01: Placeholder rule's "skip" verdict paths have zero automated test coverage

**File:** `backend/tools/placeholder_triage.py:40-80`; every test file under `backend/tests/` that touches capture/triage
**Issue:** Every single test in the phase 3 suite (`test_capture_endpoint.py`, `test_engagements_endpoint.py`, `test_capture_bedrock_failfast.py`, `test_triage_runner.py`) uses `budget=500.0` with a description containing no red-flag keyword. Confirmed via grep: no test anywhere sends a budget below `BUDGET_FLOOR` (100.0) or a description containing any of `unpaid`/`no budget`/`exposure`/`equity only`/`trial task`/`spec work`. Since this deterministic rule is the *sole* triage backend exercised by CI (D-06(b)) and gates every `/capture` call in the demo's default configuration, its two "skip" branches are shipped completely unverified by the test suite — a regression here (e.g. an inverted comparison, a typo'd keyword) would pass all 29 tests silently. I confirmed manually that the current implementation IS correct for both branches, but that correctness rests entirely on manual verification, not the suite.
**Fix:** Add direct unit tests for `placeholder_kill_switch_check` (or at minimum `_deterministic_triage_runner`) covering: budget below floor → `verdict == "skip"`; description containing a red-flag keyword → `verdict == "skip"`; and ideally one `/capture` integration test asserting the `skip` verdict end-to-end, e.g.:
```python
def test_deterministic_triage_runner_skips_low_budget():
    job = JobSlice(title="t", description="fine", budget=50.0)
    result = _deterministic_triage_runner(job)
    assert result.verdict == "skip"

def test_deterministic_triage_runner_skips_red_flag_keyword():
    job = JobSlice(title="t", description="this is unpaid exposure work", budget=500.0)
    result = _deterministic_triage_runner(job)
    assert result.verdict == "skip"
```

### WR-02: Module-level `FileEngagementStore()` construction has an eager, cwd-relative disk side effect on import

**File:** `backend/api.py:29`
**Issue:** `_store = FileEngagementStore()` runs at import time with the default `base_dir=Path("data/engagements")` (relative to whatever the process's current working directory happens to be), and `FileEngagementStore.__init__` calls `self.base_dir.mkdir(parents=True, exist_ok=True)` unconditionally. I confirmed this creates a real `backend/data/engagements/` directory on disk merely by running the test suite, even though every test overrides `get_store` via `app.dependency_overrides` and never touches `_store`. This is a wasted/unintended side effect of importing the module (harmless here because `data/` is gitignored, but it means `import api` is not pure, will silently create directories wherever the interpreter happens to be invoked from, and would break if the process's cwd is a read-only filesystem location).
**Fix:** Anchor the default path to the module location rather than cwd, and/or defer construction:
```python
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data" / "engagements"
_store = FileEngagementStore(base_dir=_DEFAULT_DATA_DIR)
```
or lazily construct via `functools.lru_cache` inside `get_store()` so import alone never touches disk.

### WR-03: `record.triage` assignment after construction is unvalidated (no `validate_assignment`)

**File:** `backend/api.py:82-84`; `backend/models/engagement_record.py:48-54`
**Issue:** `EngagementRecord` is constructed with only `job`, then `record.triage = triage_runner(job)` mutates the instance post-construction. `EngagementRecord` has no `model_config = ConfigDict(validate_assignment=True)`, so this assignment is never re-validated by Pydantic — correctness here depends entirely on `triage_runner`'s return type actually being a `TriageSlice` by convention, not by any enforced contract at the assignment site. Currently both `TriageRunner` implementations do return a real `TriageSlice` (via `.model_validate(...)`), so there is no live bug today, but it's a latent trap: any future third `TriageRunner` implementation (or a refactor that returns a plain `dict`) would silently store the wrong shape with no error until (or unless) `store.get()`'s `model_validate_json` round-trip catches it later as a `StoreCorruptError`.
**Fix:** Add `model_config = ConfigDict(validate_assignment=True)` to `EngagementRecord`, or construct the record in one shot (`EngagementRecord(job=job, triage=triage_runner(job))`) inside the try block so the type is enforced at construction rather than via mutation.

### WR-04: `GET /engagements/{id}` does not handle `StoreCorruptError`

**File:** `backend/api.py:97-105`
**Issue:** `FileEngagementStore.get()` raises `StoreCorruptError` (a `ValueError` subclass) if an on-disk record fails schema validation. `get_engagement()` only checks for `record is None` (the "not found" case) — a corrupt record is a distinct, plausible-in-production failure mode (e.g. a future schema migration leaves an old record incompatible) that this endpoint doesn't distinguish from any other unhandled error; it will bubble up as a generic 500 with no indication to the caller (or the server log path is the only place the informative `StoreCorruptError` message appears).
**Fix:**
```python
from store.file_engagement_store import StoreCorruptError
...
try:
    record = store.get(engagement_id)
except StoreCorruptError:
    raise HTTPException(status_code=500, detail="Engagement record is corrupt")
if record is None:
    raise HTTPException(status_code=404, detail="Engagement not found")
```

## Info

### IN-01: `delegate=True` on `gig_triage_agent.as_tool(...)` has no effect given the current specialist configuration

**File:** `backend/agents/supervisor.py:27-36`
**Issue:** Verified against the installed `strands-agents==1.54.0` source (`_AgentAsTool.stream()`, lines 256-298): the `if result.structured_output:` branch is checked *before* the `elif self._delegate:` branch, and `gig_triage_agent` always sets `structured_output_model=TriageSlice`. So as long as the specialist successfully produces structured output, `delegate=True` never actually changes which branch fires — the code would behave identically with `delegate=False`. This matches the supervisor.py docstring's own (accurate) claim that extraction happens "BEFORE any delegate/re-authoring logic runs," which makes the `delegate=True` argument effectively inert for the currently-shipped path (it only matters as a fallback if `result.structured_output` is ever empty, e.g. a future specialist without `structured_output_model`). Not a bug — just worth a one-line comment so a future reader doesn't assume `delegate=True` is load-bearing for ORC-02 correctness.
**Fix:** Add a short comment at the `delegate=True` line noting it's a fallback-only setting, not the primary extraction mechanism (which is `structured_output`).

### IN-02: `TriageSlice.score` has no range constraint

**File:** `backend/models/engagement_record.py:25-28` (pre-existing, but directly consumed by all new Phase 3 code)
**Issue:** `score: float` accepts any float, including negative values or values >1.0. The placeholder rule only ever emits `0.1` or `0.6`, so this is not exercised today, but nothing structurally prevents a future triage backend from emitting an out-of-range score that flows straight through to `CaptureResponse.score` unchecked.
**Fix:** Consider `score: float = Field(ge=0.0, le=1.0)` if the score is meant to be a normalized confidence value (confirm intended range with the PRD before changing, since this file wasn't part of this phase's diff).

---

_Reviewed: 2026-09-02T22:16:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
