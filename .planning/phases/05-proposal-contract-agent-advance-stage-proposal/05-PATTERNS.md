# Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal") - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 9 (new/modified)
**Analogs found:** 9 / 9

RESEARCH.md does not exist for this phase (not yet written) — file list and pattern
targets derived from `05-CONTEXT.md`'s `<code_context>` and `<decisions>` alone, per
instructions. All analog paths below verified git-tracked via `git ls-files`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/agents/proposal_contract_agent.py` (NEW) | service (specialist Agent builder) | request-response | `backend/agents/gig_triage_agent.py` | exact |
| `backend/agents/proposal_runner.py` (NEW) | service (DI seam) | request-response | `backend/agents/triage_runner.py` | exact |
| `backend/tools/check_scope_clarity.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/placeholder_triage.py` | exact |
| `backend/tools/draft_proposal.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/placeholder_triage.py` | exact |
| `backend/tools/draft_contract.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/placeholder_triage.py` | exact |
| `backend/agents/supervisor.py` (MODIFY — add proposal specialist wiring + `extract_proposal_result`) | service (orchestrator) | request-response | itself (`build_supervisor`/`extract_triage_result`, this file, lines 22-65) | exact (extend in place) |
| `backend/api.py` (MODIFY — add `POST /engagements/{id}/advance`) | route/controller | request-response | `capture` handler + `map_bedrock_error`, this file, lines 62-121 | exact (extend in place) |
| `backend/models/engagement_record.py` (MODIFY — enrich `ProposalSlice`/`ContractSlice`, add milestone model + specialist result model) | model | CRUD | itself, lines 31-45 (existing `ProposalSlice`/`ContractSlice`) | exact (extend in place) |
| `backend/tests/test_advance_endpoint.py`, `test_proposal_runner.py`, `test_advance_bedrock_failfast.py` (NEW) | test | request-response | `test_capture_endpoint.py`, `test_capture_bedrock_failfast.py`, `conftest.py` | exact |

## Pattern Assignments

### `backend/agents/proposal_runner.py` (service, request-response)

**Analog:** `backend/agents/triage_runner.py` (verified tracked)

**Full pattern to mirror (lines 1-56 of the analog)** — module docstring establishes the
single-writer rationale for placement under `agents/`, then:

```python
from __future__ import annotations

import os
from typing import Protocol

from models.engagement_record import JobSlice, TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check


class TriageRunner(Protocol):
    def __call__(self, job: JobSlice) -> TriageSlice: ...


def _deterministic_triage_runner(job: JobSlice) -> TriageSlice:
    result = placeholder_kill_switch_check(job.budget, job.description)
    return TriageSlice.model_validate(result)


def _supervisor_triage_runner(job: JobSlice) -> TriageSlice:
    from agents.supervisor import build_supervisor, extract_triage_result

    supervisor = build_supervisor()
    supervisor(f"Triage this job: {job.model_dump_json()}")
    return extract_triage_result(supervisor.messages)


def get_triage_runner() -> TriageRunner:
    backend = os.environ.get("TRIAGE_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_triage_runner
    return _deterministic_triage_runner
```

**Rename mapping for Phase 5:**
- `TriageRunner` (Protocol) → `ProposalRunner`, `__call__(self, record: EngagementRecord) -> ProposalContractResult` (or `job: JobSlice` if the deterministic body only needs job fields — CONTEXT.md D-05 says the guard (`triage exists and verdict == "apply"`) happens in `api.py` before calling the runner, so the runner itself likely only needs `job: JobSlice` plus maybe `triage: TriageSlice` for context — Claude's discretion per D-01's "Module layout ... discretion").
- `_deterministic_triage_runner` → `_deterministic_proposal_runner`: calls `check_scope_clarity` as a plain function first (deterministic gate, D-03), then `draft_proposal`/`draft_contract` as plain functions, and assembles the ONE typed result object (D-01's mutually-exclusive schema) — NOT two separate typed slices merged ad hoc; build the single result model first, split into slices only in `api.py`'s merge step.
- `_supervisor_triage_runner` → `_supervisor_proposal_runner`: identical shape — `from agents.supervisor import build_supervisor, extract_proposal_result`; construct supervisor; invoke with a prompt carrying the record/job; extract via the new `extract_proposal_result`.
- `get_triage_runner`/`TRIAGE_BACKEND` → `get_proposal_runner`/`PROPOSAL_BACKEND` (per D-02), same default `"placeholder"` semantics, same `os.environ.get(..., "placeholder")` read.
- **Module placement:** under `backend/agents/` (not top-level) — same single-writer-guard rationale as the analog's docstring lines 1-14; `test_single_writer.py` scans `agents/` and `tools/`, so this placement is load-bearing, not cosmetic.
- **Must NOT import the store** — same guard.

---

### `backend/agents/proposal_contract_agent.py` (service, request-response)

**Analog:** `backend/agents/gig_triage_agent.py` (verified tracked, full file, 39 lines)

**Imports + construction pattern (lines 12-38, entire file)**:
```python
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_gig_triage_agent() -> Agent:
    """Construct (do not invoke) the Gig Triage specialist Agent."""
    return Agent(
        name="gig_triage_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(...),
        tools=[placeholder_kill_switch_check],
        structured_output_model=TriageSlice,
    )
```

**Critical invariant (docstring lines 1-11):** Construction must perform NO network call —
only invoking the returned `Agent` touches Bedrock. This is what lets the offline
construction test (D-07(f): "the app + Supervisor + Proposal-Contract Agent construct
without creds") pass. Do not add any eager Bedrock call (e.g. a model-list ping) in
`build_proposal_contract_agent()`.

**Rename mapping:** `build_gig_triage_agent` → `build_proposal_contract_agent`; `name="gig_triage_agent"` → `name="proposal_contract_agent"`; `tools=[placeholder_kill_switch_check]` → `tools=[check_scope_clarity, draft_proposal, draft_contract]`; `structured_output_model=TriageSlice` → the new mutually-exclusive typed result model (D-01) — e.g. `ProposalContractResult`. Reuse the same `MODEL_ID`/`REGION` env-var pattern verbatim (do not hardcode a different model id).

---

### `backend/tools/check_scope_clarity.py`, `draft_proposal.py`, `draft_contract.py` (utility, transform, dual-use)

**Analog:** `backend/tools/placeholder_triage.py` (verified tracked, full file, 81 lines)

**Dual-use pattern to replicate (lines 1-49 excerpt: docstring rationale + decorator + signature)**:
```python
from __future__ import annotations

from strands import tool


@tool
def placeholder_kill_switch_check(budget: float | None, description: str) -> dict:
    """... Returns a plain dict with keys verdict, score, reasoning ... No LLM
    call, no randomness — the same input always produces the same output."""
    ...
    return {"verdict": "skip", "score": 0.1, "reasoning": "..."}
```

**Rules for the three new tools (D-03):**
- Each is `@tool`-decorated (`from strands import tool`), callable both as a plain Python
  function (deterministic `ProposalRunner` path) AND registered on the specialist `Agent`
  (live path) — same as this analog's docstring lines 10-18 explains.
- Each returns a **plain dict** (auto-wrapped by strands into a `ToolResult`), matching a
  slice of the eventual typed result model.
- Each is the ONE source of truth for its rule — no duplicate logic in the deterministic
  runner vs. the live Agent path.
- **Must NOT import the store** (docstring lines 19-21 of analog: "single-writer guard,
  REC-03/D-05 — `backend/tests/test_single_writer.py` scans `backend/tools/` for store
  imports").
- `check_scope_clarity(budget: float | None, timeline: str | None, deliverables: list[str] | None) -> dict` — deterministic gate mirroring the analog's budget-floor + keyword-scan structure (lines 50-80): flag missing budget/timeline/deliverables and produce `needs_human_input`/`question` fields directly, since D-01 says these are first-class from the start.
- `draft_proposal(job: dict, ...) -> dict` — phased-scope proposal text/structure.
- `draft_contract(job: dict, proposal: dict, ...) -> dict` — SOW with deliverables + milestones + typed payment schedule (see `ContractSlice` enrichment below).

---

### `backend/agents/supervisor.py` (MODIFY — extend, do not replace)

**Analog:** itself, lines 22-65 (verified tracked)

**`build_supervisor` pattern (lines 22-43)** — agents-as-tools wiring:
```python
def build_supervisor() -> Agent:
    gig_triage_agent = build_gig_triage_agent()
    triage_tool = gig_triage_agent.as_tool(
        name="gig_triage_agent",
        description=(...),
        delegate=True,  # verified-compatible: BedrockModel.stateful == False
    )
    return Agent(
        system_prompt=(
            "You route every triage request to the gig_triage_agent tool. "
            "Never answer yourself."
        ),
        tools=[triage_tool],
    )
```

**D-04 requires a DISTINCT second specialist,** observable as a separate invocation in a
live trace — extend `build_supervisor()` (or add a stage-scoped builder, per D-01's
"Claude's discretion: ... whether the live path extends `build_supervisor()` or uses a
stage-scoped builder"). If extending in place: wrap `build_proposal_contract_agent()` the
same way (`.as_tool(name="proposal_contract_agent", description=..., delegate=True)`),
add it to `tools=[triage_tool, proposal_tool]`, and update the system prompt to route by
request type (do NOT let the Supervisor re-author either specialist's output — D-02).

**`extract_triage_result` pattern (lines 46-65) — mirror EXACTLY as `extract_proposal_result`:**
```python
def extract_triage_result(supervisor_messages: list[dict]) -> TriageSlice:
    """Walk supervisor.messages for the first toolResult content block
    containing a "json" entry and validate it into a TriageSlice.
    Never reads the Supervisor's own final text answer (D-02)."""
    for message in supervisor_messages:
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            tool_result = block["toolResult"]
            if not isinstance(tool_result, dict):
                continue
            for content_block in tool_result.get("content", []):
                if isinstance(content_block, dict) and "json" in content_block:
                    return TriageSlice.model_validate(content_block["json"])
    raise RuntimeError("gig_triage_agent tool result not found in supervisor trace")
```
Rename to `extract_proposal_result(supervisor_messages) -> ProposalContractResult`,
swap the target tool name in the not-found error message, and validate into the new
mutually-exclusive result model instead of `TriageSlice`. This is the load-bearing
ORC-02-style mechanism — it reads the toolResult block emitted BEFORE any
delegate/re-authoring logic runs, and never inspects the Supervisor's own final answer.
If two specialists are both wired in, you may need to match on tool name in the
`toolResult`'s `toolUseId`/block structure to disambiguate which specialist's result
you're extracting — verify against the installed strands-agents message shape before
assuming a single scan is sufficient with two tools registered.

---

### `backend/api.py` (MODIFY — add `POST /engagements/{id}/advance`)

**Analog:** the `capture` handler + `map_bedrock_error`, this file, lines 62-121 (verified tracked)

**Handler shape to mirror (lines 97-121)**:
```python
@app.post("/capture", response_model=CaptureResponse)
def capture(
    job: JobSlice,
    store: Annotated[EngagementStore, Depends(get_store)],
    triage_runner: Annotated[TriageRunner, Depends(get_triage_runner)],
) -> CaptureResponse:
    record = EngagementRecord(job=job)
    try:
        record.triage = triage_runner(job)  # typed, VERBATIM merge (D-02/ORC-02)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped
    store.create(record)
    return CaptureResponse(...)
```

**`GET /engagements/{id}` shape to mirror for the load-and-404 step (lines 124-132)**:
```python
@app.get("/engagements/{engagement_id}", response_model=EngagementRecord)
def get_engagement(
    engagement_id: UUID,
    store: Annotated[EngagementStore, Depends(get_store)],
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return record
```

**New `/advance` handler — compose both shapes plus a new guard (D-05):**
```python
@app.post("/engagements/{engagement_id}/advance", response_model=EngagementRecord)
def advance(
    engagement_id: UUID,
    stage: Literal["proposal"],           # Phase 6 adds "ops" without a rewrite (D-05)
    store: Annotated[EngagementStore, Depends(get_store)],
    proposal_runner: Annotated[ProposalRunner, Depends(get_proposal_runner)],
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if record.triage is None or record.triage.verdict != "apply":
        raise HTTPException(status_code=409, detail="Engagement is not apply-triaged")
    try:
        result = proposal_runner(record.job)  # or record, per runner signature
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped
    # VERBATIM merge — split the ONE typed result into proposal (+contract on
    # happy path) slices, no Supervisor re-authoring (D-02/D-05).
    record.proposal = result.to_proposal_slice()
    if not result.needs_human_input:
        record.contract = result.to_contract_slice()
    store.save(record)
    return record
```
`map_bedrock_error` (lines 62-94) is reused **directly, unmodified** — do not fork a
second copy for `/advance`; it already covers `NoCredentialsError`, `ClientError`,
`ModelThrottledException`, `ContextWindowOverflowException`, `BotoCoreError`, and a
catch-all, exactly per D-05/D-07(g)'s "reuse Phase 3's `map_bedrock_error`."

**409 vs 422 for the non-apply guard:** D-01 in CONTEXT.md leaves this to discretion;
`409 Conflict` is the better HTTP-semantic fit here (the resource exists but is in the
wrong state for the requested transition) — recommend 409, but this is not load-bearing
either way since it's explicitly "Claude's discretion."

**`store.save(record)` vs `store.create(record)`:** note the analog's `capture` uses
`store.create` (new record); `/advance` mutates an EXISTING record, so use
`store.save(record)` per D-05's explicit text ("persists via the existing
`store.save(record)`") — confirm `EngagementStore`'s protocol exposes `save` (it does,
per `backend/store/engagement_store.py`/`file_engagement_store.py`, referenced in
CONTEXT.md's Reusable Assets).

---

### `backend/models/engagement_record.py` (MODIFY — enrich, do not replace)

**Analog:** itself, lines 31-45 (verified tracked)

**Current stubs to enrich (lines 31-39)**:
```python
class ProposalSlice(BaseModel):
    text: Optional[str] = None
    needs_human_input: bool = False
    question: Optional[str] = None


class ContractSlice(BaseModel):
    text: Optional[str] = None
    payment_schedule: list[dict] = Field(default_factory=list)
```

**D-06 requires tightening `payment_schedule` from `list[dict]` to a typed milestone
model.** Follow the file's existing style (plain `BaseModel`, `Optional[...] = None` for
stage-not-yet-run fields, `Field(default_factory=list)` for collections):
```python
class PaymentMilestone(BaseModel):
    label: str
    amount: float
    due_marker: str  # e.g. "on signing", "on delivery of phase 1"


class ContractSlice(BaseModel):
    text: Optional[str] = None
    payment_schedule: list[PaymentMilestone] = Field(default_factory=list)
```

**New mutually-exclusive specialist result model (D-01)** — define alongside the slices
(same module, matching style) so it's importable by both `proposal_runner.py` and
`supervisor.py`'s `extract_proposal_result`:
```python
class ProposalContractResult(BaseModel):
    needs_human_input: bool = False
    question: Optional[str] = None
    proposal_text: Optional[str] = None
    contract_text: Optional[str] = None
    payment_schedule: list[PaymentMilestone] = Field(default_factory=list)
    # add a model_validator if you want to enforce SC3's mutual exclusivity
    # structurally (needs_human_input=True <=> contract_text is None), rather
    # than relying solely on the deterministic tool bodies to uphold it.
```
Whether SC3 is enforced via a Pydantic `model_validator` or left to the deterministic
tool logic + tests is open per D-01's discretion note on "exact typed result model
name/shape" — a `model_validator(mode="after")` raising on both-populated is the
stronger, more test-visible guarantee and is recommended given SC3 is called out as
"the structural anti-guessing guard."

---

### Tests — mirror these three analogs directly

**`test_advance_endpoint.py`** ← analog `backend/tests/test_capture_endpoint.py` (full file,
53 lines, verified tracked). Same `client` fixture usage (from `conftest.py`, unchanged —
no new fixture needed), same "POST then GET round-trips" shape (lines 25-44), same
malformed-payload → 422 pattern (lines 47-52) adapted to `/advance`'s guards (404 unknown
id, 409 non-apply).

**`test_advance_bedrock_failfast.py`** ← analog `backend/tests/test_capture_bedrock_failfast.py`
(full file, 83 lines, verified tracked). Identical `app.dependency_overrides[...] = lambda: _raising_runner(exc)` / `try/finally: del app.dependency_overrides[...]` pattern (lines 15-19, 34-41), same
`pytest.mark.parametrize` over `ModelThrottledException`, `ContextWindowOverflowException`,
`RuntimeError`, `ClientError`, `NoCredentialsError` — just swap `get_triage_runner` for
`get_proposal_runner` and `/capture` for `/advance`.

**`test_proposal_runner.py`** ← analog would be `test_triage_runner.py` if present (not
read in this pass — verify its existence/shape at plan time); at minimum mirror
`conftest.py`'s `client`/`file_store` fixture pattern (lines 1-28, verified tracked) for
any endpoint-level test, and directly unit-test `_deterministic_proposal_runner` as a
plain function call (no TestClient needed) the way `_deterministic_triage_runner` in
`triage_runner.py` is a plain, directly-callable function.

**`test_single_writer.py`** — NO modification needed; it already scans `agents/` and
`tools/` recursively (`SCAN_DIRS = ["agents", "tools"]`, lines 13, 31-39) and will
automatically cover the four new Phase-5 files. Just ensure none of
`proposal_runner.py`, `proposal_contract_agent.py`, `check_scope_clarity.py`,
`draft_proposal.py`, `draft_contract.py` import `store` or `backend.store`.

## Shared Patterns

### Single-writer rule (REC-03/D-05)
**Source:** `backend/tests/test_single_writer.py` (AST-based import scan, lines 9-43)
**Apply to:** every new file under `backend/agents/` and `backend/tools/` — none may
import `store` or `backend.store`. Only `backend/api.py` calls `store.get`/`store.save`.

### Deterministic-first DI seam + env-selected live path
**Source:** `backend/agents/triage_runner.py` (full file)
**Apply to:** `backend/agents/proposal_runner.py` — `ProposalRunner` Protocol,
`_deterministic_proposal_runner`, `_supervisor_proposal_runner`, `get_proposal_runner`
reading `PROPOSAL_BACKEND` (default `"placeholder"`).

### Bedrock fail-fast, credential-free 503
**Source:** `backend/api.py` lines 53-94 (`BedrockUnavailableError`, `map_bedrock_error`)
**Apply to:** the new `/advance` handler — reuse unmodified, do not fork.

### VERBATIM typed merge, no Supervisor re-authoring
**Source:** `backend/api.py` line 105 comment + `backend/agents/supervisor.py` lines 46-65
(`extract_triage_result` reads the toolResult block, never final text)
**Apply to:** `/advance`'s merge step and the new `extract_proposal_result`.

### Dual-use `@tool` (plain-Python + Agent-registered), single rule body
**Source:** `backend/tools/placeholder_triage.py` (full file)
**Apply to:** `check_scope_clarity.py`, `draft_proposal.py`, `draft_contract.py`.

## No Analog Found

None — all Phase 5 files have a strong, same-role-and-flow analog from Phase 3.

## Metadata

**Analog search scope:** `backend/agents/`, `backend/tools/`, `backend/api.py`,
`backend/models/`, `backend/tests/`
**Files scanned:** 10 (9 read in full + `test_single_writer.py`)
**Tracked-source gate:** all 10 analog paths verified via `git ls-files` (non-empty
output for every path) — no gitignored mirror paths present in this repo layout.
**Pattern extraction date:** 2026-09-05
