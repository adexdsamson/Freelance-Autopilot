# Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring - Pattern Map

**Mapped:** 2026-09-08
**Files analyzed:** 10 (new/modified)
**Analogs found:** 10 / 10 (fixtures/loader = new pattern, no direct analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/agents/ops_agent.py` (NEW `build_ops_agent()`) | service (specialist Agent builder) | request-response | `backend/agents/proposal_contract_agent.py` | exact |
| `backend/agents/ops_runner.py` (NEW `OpsRunner`) | service (DI seam) | request-response | `backend/agents/proposal_runner.py` | exact |
| `backend/agents/supervisor.py` (ADD `build_full_supervisor` + extractor) | service (orchestrator) | request-response | same file's `build_proposal_supervisor`/`extract_proposal_result` | exact |
| `backend/tools/check_scope_creep.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/check_scope_clarity.py` | exact |
| `backend/tools/check_invoice_status.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/check_scope_clarity.py` | exact |
| `backend/tools/draft_status_update.py` (NEW) | utility (dual-use `@tool`) | transform | `backend/tools/draft_proposal.py` / `draft_contract.py` | exact |
| `backend/fixtures/*.json` + loader | config/utility (pure data) | file-I/O | none existing — new pattern | no analog |
| `backend/api.py` (extend `/advance` `elif stage == "ops"`) | controller (route handler) | request-response | same file's `stage == "proposal"` branch | exact |
| `backend/models/engagement_record.py` (enrich `OpsSlice`) | model | CRUD | same file's `ProposalSlice`/`ContractSlice`/`ProposalContractResult`/`PaymentMilestone` | exact |
| `backend/tests/test_ops_*.py` (NEW) | test | request-response / transform | `backend/tests/test_proposal_runner.py`, `test_proposal_supervisor_wiring.py`, `test_advance_endpoint.py`, `test_single_writer.py` | exact |

## Pattern Assignments

### `backend/agents/ops_agent.py` (service, request-response)

**Analog:** `backend/agents/proposal_contract_agent.py` (also reference `backend/agents/gig_triage_agent.py` for the placeholder-comment style)

**Imports pattern** (proposal_contract_agent.py lines 17-27):
```python
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import ProposalContractResult
from tools.check_scope_clarity import check_scope_clarity
from tools.draft_contract import draft_contract
from tools.draft_proposal import draft_proposal

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")
```
For ops_agent.py: swap the three tool imports for `check_scope_creep`, `check_invoice_status`, `draft_status_update`, and swap `ProposalContractResult` for whatever typed ops result model is chosen (e.g. `OpsResult`, defined in `engagement_record.py`).

**Core builder pattern** (lines 33-50):
```python
def build_proposal_contract_agent() -> Agent:
    """Construct (do not invoke) the Proposal-Contract specialist Agent."""
    return Agent(
        name="proposal_contract_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Proposal-Contract specialist. Always call "
            "check_scope_clarity first with the job's budget and "
            "description. If it reports the scope is not clear, do NOT "
            "guess -- return needs_human_input=True with its question "
            "verbatim. Only when the scope is clear should you call "
            "draft_proposal, then draft_contract with the drafted "
            "proposal text, and return the resulting proposal_text, "
            "contract_text, and payment_schedule."
        ),
        tools=[check_scope_clarity, draft_proposal, draft_contract],
        structured_output_model=ProposalContractResult,
    )
```
Mirror exactly: `name="ops_agent"`, system prompt sequencing "always call check_scope_creep and check_invoice_status, then draft_status_update reflecting active flags", `tools=[check_scope_creep, check_invoice_status, draft_status_update]`, `structured_output_model=<OpsResult>`.

**Critical invariant (docstring convention to copy verbatim style):** construction performs NO network call — only invoking the Agent touches Bedrock (see proposal_contract_agent.py lines 10-12, gig_triage_agent.py lines 9-10). Also copy the single-writer guard docstring (proposal_contract_agent.py lines 14-15): "This module must NOT import the store."

---

### `backend/agents/ops_runner.py` (service, request-response)

**Analog:** `backend/agents/proposal_runner.py` (full file, 83 lines — small enough for one read)

**Protocol + deterministic path** (lines 29-57):
```python
class ProposalRunner(Protocol):
    def __call__(self, job: JobSlice) -> ProposalContractResult: ...


def _deterministic_proposal_runner(job: JobSlice) -> ProposalContractResult:
    clarity = check_scope_clarity(job.budget, job.description)
    if not clarity["clear"]:
        return ProposalContractResult(
            needs_human_input=True,
            question=clarity["question"],
        )
    proposal = draft_proposal(job.title, job.description, job.budget)
    contract = draft_contract(
        job.title, job.description, proposal["proposal_text"], job.budget
    )
    return ProposalContractResult(
        proposal_text=proposal["proposal_text"],
        contract_text=contract["contract_text"],
        payment_schedule=contract["payment_schedule"],
    )
```
For `OpsRunner`: signature likely `__call__(self, contract: ContractSlice, client_thread: list[dict], payment_schedule: list[PaymentMilestone]) -> OpsResult` (per D-03: runner takes record's contract SOW + loaded fixture thread + payment schedule). Compose `check_scope_creep` + `check_invoice_status` + `draft_status_update` as plain Python calls, same pattern.

**Live/supervisor path — lazy import to avoid circular/not-yet-defined imports** (lines 60-74):
```python
def _supervisor_proposal_runner(job: JobSlice) -> ProposalContractResult:
    from agents.supervisor import build_proposal_supervisor, extract_proposal_result

    supervisor = build_proposal_supervisor()
    supervisor(f"Draft a proposal and contract for this job: {job.model_dump_json()}")
    return extract_proposal_result(supervisor.messages)
```
For ops: `from agents.supervisor import build_full_supervisor, extract_ops_result` (or whatever name-disambiguated extractor is chosen per D-01), invoke with a prompt embedding the contract/thread/schedule payload, then extract.

**Env-selected DI seam** (lines 77-82):
```python
def get_proposal_runner() -> ProposalRunner:
    backend = os.environ.get("PROPOSAL_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_proposal_runner
    return _deterministic_proposal_runner
```
Mirror as `get_ops_runner()` reading `OPS_BACKEND` (default `"placeholder"`).

**Docstring convention to copy** (lines 1-17): module-level note that this file lives under `backend/agents/` (not top-level) specifically so `test_single_writer.py`'s scan covers it, and it must NEVER import the store.

---

### `backend/agents/supervisor.py` (service, request-response) — MODIFY existing file

**Analog:** the SAME file's `build_proposal_supervisor`/`extract_proposal_result` (lines 69-117), which itself generalizes `build_supervisor`/`extract_triage_result` (lines 23-66).

**Stage-scoped supervisor pattern to mirror once more, but this time as the UNIFIED 3-tool supervisor** (lines 23-44, `build_supervisor`):
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
For `build_full_supervisor()`: build all three specialists (`build_gig_triage_agent`, `build_proposal_contract_agent`, `build_ops_agent`), wrap each with `.as_tool(name=..., description=..., delegate=True)`, and register all three in one `Agent(tools=[triage_tool, proposal_tool, ops_tool])` whose system prompt routes to whichever specialist fits the request (not a single blind "always call X" — three choices now).

**IMPORTANT constraint from context (D-01):** do NOT delete or modify `build_supervisor`/`build_proposal_supervisor` — `build_full_supervisor` is additive, third function in the same file, matching how `build_proposal_supervisor` was added alongside `build_supervisor` without altering it (see `test_build_supervisor_unchanged_not_extended` in test_proposal_supervisor_wiring.py, lines 37-48 — a directly analogous "must stay single-tool per legacy supervisor" test that the new phase's tests should extend to a three-way check).

**Extraction pattern — generalize by tool name (D-01 disambiguation)** (lines 47-66, single-tool scan to generalize):
```python
def extract_triage_result(supervisor_messages: list[dict]) -> TriageSlice:
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
The new name-disambiguated extractor (e.g. `extract_ops_result` or a shared `extract_result_by_tool_name(messages, tool_use_id_or_name, Model)`) must walk `toolUse` blocks to capture `toolUseId -> name`, THEN match the corresponding `toolResult.toolUseId` before reading its `json` content block — this is the toolUseId↔name disambiguation Phase 5 deferred (context lines 42-46). Preserve the exact defensive `isinstance` guards (never index blindly) — see `test_extract_proposal_result_tolerates_malformed_content_blocks` for the required robustness contract.

---

### `backend/tools/check_scope_creep.py` (utility, transform)

**Analog:** `backend/tools/check_scope_clarity.py` (full file, 76 lines)

**Dual-use `@tool` + docstring/single-writer-guard convention** (lines 1-25, 48-56):
```python
from __future__ import annotations

import re

from strands import tool

@tool
def check_scope_clarity(budget: float | None, description: str) -> dict:
    """Deterministic gate (no LLM): ...
    Returns a plain dict with keys "clear" (bool) and "question" (str | None).
    The same input always produces the same output.
    """
```
Module docstring (lines 1-20) explains: this is the ONE source of truth, called directly as plain Python by the deterministic runner AND registered on the specialist Agent for the live path; must NOT import the store (single-writer guard).

For `check_scope_creep(sow_deliverables: list[str], client_thread: list[dict]) -> dict`: compare thread messages against the SOW's enumerated deliverables (word/keyword scan analogous to `TIMELINE_MARKERS`/`DELIVERABLE_MARKERS`, lines 37-45 of check_scope_clarity.py), returning e.g. `{"creep_detected": bool, "flags": [...]}`. Reuse the `_contains_marker` word-boundary helper pattern if keyword matching is used (lines 41-45).

---

### `backend/tools/check_invoice_status.py` (utility, transform)

**Analog:** `backend/tools/draft_contract.py` for the payment-schedule shape (`PaymentMilestone`/`due_marker`, lines 37-67) + `check_scope_clarity.py` for the dual-use `@tool` gate structure.

Reuse the `PaymentMilestone`/`due_marker` shape (label/amount/due_marker — see engagement_record.py lines 37-41 and draft_contract.py lines 51-67) to determine "overdue": compare a milestone's `due_marker` against the fixture's implied elapsed time / a demo "today" marker, returning `{"invoice_flags": [...]}` per milestone judged overdue.

---

### `backend/tools/draft_status_update.py` (utility, transform)

**Analog:** `backend/tools/draft_proposal.py` (full file, 39 lines) — deterministic template drafter.

```python
@tool
def draft_proposal(title: str, description: str, budget: float) -> dict:
    """Draft a phased-scope proposal ...
    Deterministic template — no LLM call, no randomness; the same input
    always produces the same output (demo-determinism). Returns a plain
    dict with key "proposal_text".
    """
    ...
    return {"proposal_text": proposal_text}
```
For `draft_status_update(scope_creep_flags: list[dict], invoice_flags: list[dict]) -> dict`: deterministic string template reflecting whichever flags are active (OPS-03/SC4), returning `{"status_update_text": str}`. Same "no LLM, same input -> same output" determinism guarantee, same dual-use `@tool` decorator, same "must not import the store" docstring note.

---

### `backend/fixtures/*.json` + loader (config, file-I/O) — NEW PATTERN, NO ANALOG

No existing fixture directory or loader exists in this codebase (`ls backend/fixtures` returns nothing). Nearest precedent for "sample data used by tests" is the inline literal dicts/JobSlice constructions in `backend/tests/test_proposal_runner.py` (e.g. `CLEAR_DESCRIPTION`/`AMBIGUOUS_DESCRIPTION` constants, lines 16-20) — but those are Python literals, not JSON files with a loader.

Recommended approach (Claude's discretion per context lines 111-117): a small `backend/fixtures/loader.py` (or a function in `ops_runner.py`) doing plain `json.loads(Path(...).read_text())` — pure Python, no framework dependency, mirrors the "no import the store" and "no network" purity already enforced elsewhere. Files needed: `sample_client_thread.json` + a clean variant, `sample_payment_schedule.json` + a clean variant, `sample_upwork_jobs.json`. Selector mechanism: an `/advance` query param (e.g. `fixture=creep|clean`) threaded through to `get_ops_runner`/the runner call, analogous to how `stage` is already a query param on `/advance` (api.py line 155).

---

### `backend/api.py` (controller, request-response) — MODIFY existing `/advance` handler

**Analog:** the SAME file's existing `stage == "proposal"` branch (lines 153-208)

**Guard + typed VERBATIM merge + fail-fast 503 pattern to replicate** (lines 159-207):
```python
@app.post("/engagements/{engagement_id}/advance", response_model=EngagementRecord)
def advance(
    engagement_id: UUID,
    stage: str,
    store: Annotated[EngagementStore, Depends(get_store)],
    proposal_runner: Annotated[ProposalRunner, Depends(get_proposal_runner)],
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if stage != "proposal":
        raise HTTPException(status_code=400, detail=f"unsupported stage '{stage}'")

    if record.triage is None or record.triage.verdict != "apply":
        raise HTTPException(
            status_code=409,
            detail="engagement is not apply-triaged; cannot draft a proposal",
        )

    try:
        result: ProposalContractResult = proposal_runner(record.job)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped

    record.proposal = ProposalSlice(...)
    if result.needs_human_input:
        record.contract = None
    else:
        record.contract = ContractSlice(...)
    store.save(record)
    return record
```
For `elif stage == "ops":` (D-05): add `ops_runner: Annotated[OpsRunner, Depends(get_ops_runner)]` as a new handler param; guard precondition "a contract/SOW must exist" (`record.contract is None` -> 4xx, choose 409 to match the proposal-stage precedent); call `ops_runner(record.contract, fixture_thread, fixture_schedule)` inside the same `try/except HTTPException / except Exception -> map_bedrock_error -> 503` shape; merge the typed ops result VERBATIM into `record.ops = OpsSlice(...)`; `store.save(record)`; `return record`. The `if stage != "proposal": raise ...` guard becomes `if stage == "proposal": ... elif stage == "ops": ... else: raise HTTPException(400, ...)` (context line 165-167 flags this exact spot as the pre-stubbed seam).

Reuse `map_bedrock_error` unchanged (lines 80-112) — no new mapping logic needed.

---

### `backend/models/engagement_record.py` (model, CRUD) — MODIFY existing `OpsSlice`

**Analog:** the SAME file's `ProposalSlice`/`ContractSlice`/`PaymentMilestone`/`ProposalContractResult` (lines 31-103)

**Typed-list-of-cards pattern to replicate** (`PaymentMilestone`, lines 37-41):
```python
class PaymentMilestone(BaseModel):
    label: str
    amount: float
    due_marker: str
```
**Result-with-validator pattern** (`ProposalContractResult`, lines 49-103) — mutual-exclusivity `@model_validator(mode="after")` enforcing structural invariants (SC3-equivalent for ops: e.g. zero-cards-on-clean vs exactly-two-cards-on-creep is enforced by the TOOL logic, not the schema, but the typed-card shape itself should follow this file's convention).

Current stub to enrich (lines 106-109):
```python
class OpsSlice(BaseModel):
    status_updates: list[dict] = Field(default_factory=list)
    scope_creep_flags: list[dict] = Field(default_factory=list)
    invoice_flags: list[dict] = Field(default_factory=list)
```
Recommended typed enrichment (D-07, Claude's discretion on exact names): define `ScopeCreepFlag(BaseModel)`, `InvoiceFlag(BaseModel)`, `StatusUpdate(BaseModel)` (or one shared `EscalationCard(BaseModel)` with a `kind: Literal["scope_creep","invoice_overdue"]` discriminator per OPS-04's "distinct escalation card" requirement), then retype `OpsSlice` to `list[ScopeCreepFlag]` etc., mirroring `list[PaymentMilestone]` at line 46. Also likely need an `OpsResult` model analogous to `ProposalContractResult` (the runner's typed return value, later merged VERBATIM into `record.ops`).

---

### `backend/tests/test_ops_*.py` (test, request-response / transform)

**Analogs:**
- `backend/tests/test_proposal_runner.py` (full file, 212 lines) — unit-depth tool + runner tests, env-selection tests (lines 204-211: `get_proposal_runner` env switch pattern to mirror for `get_ops_runner`/`OPS_BACKEND`).
- `backend/tests/test_proposal_supervisor_wiring.py` (full file, 168 lines) — construction-only Agent/tool_names assertions (lines 19-58: `isinstance(agent, Agent)`, `"tool_name" in agent.tool_names`, `supervisor is not specialist_agent` distinct-instance checks) + toolResult-extraction tests with a `_toolresult_message` helper (lines 61-73) and malformed-input robustness test (lines 149-167) — mirror for the ops extractor and for a NEW test asserting `build_full_supervisor().tool_names` contains all three specialist names (SC1, ORC-01) and that four distinct `Agent` instances exist.
- `backend/tests/test_single_writer.py` (full file, 44 lines) — the AST-based store-import guard that automatically covers any new file dropped under `backend/agents/` or `backend/tools/`; no test changes needed here, but new ops modules MUST pass it (never import `store`/`backend.store`).
- `backend/tests/test_advance_endpoint.py` / `test_advance_bedrock_failfast.py` (existing, read for the `/advance` proposal-stage endpoint test shape) — mirror for `/advance?stage=ops` success + 409 (no contract) + 503 (mapped Bedrock failure) cases, plus the full capture→proposal→ops progression test called out in context (SC5, API-03).

## Shared Patterns

### Dual-use `@tool` decorator (deterministic + live paths share one body)
**Source:** `backend/tools/check_scope_clarity.py` lines 21-25, 48-56 (also `draft_proposal.py`, `draft_contract.py`, `placeholder_triage.py`)
**Apply to:** `check_scope_creep.py`, `check_invoice_status.py`, `draft_status_update.py`
```python
from strands import tool

@tool
def some_tool(...) -> dict:
    """Deterministic (no LLM, no randomness): same input -> same output.
    Returns a plain dict with keys [...]."""
    ...
    return {...}
```
Called directly as a plain Python function by the deterministic runner path, AND registered as a tool on the specialist Agent for the live path. Never import the store (checked by `test_single_writer.py`'s AST scan of `backend/agents/` and `backend/tools/`).

### DI seam: Protocol + two implementations + env switch
**Source:** `backend/agents/proposal_runner.py` (whole file) / `backend/agents/triage_runner.py` (whole file)
**Apply to:** `backend/agents/ops_runner.py`
```python
class XRunner(Protocol):
    def __call__(self, ...) -> XResult: ...

def _deterministic_x_runner(...) -> XResult: ...  # pure Python, no Bedrock
def _supervisor_x_runner(...) -> XResult:          # lazy import agents.supervisor
    from agents.supervisor import build_full_supervisor, extract_x_result
    ...

def get_x_runner() -> XRunner:
    backend = os.environ.get("X_BACKEND", "placeholder")
    return _supervisor_x_runner if backend == "supervisor" else _deterministic_x_runner
```

### Agents-as-tools supervisor + toolResult extraction by name
**Source:** `backend/agents/supervisor.py` (whole file)
**Apply to:** `build_full_supervisor()` + its extractor
- `specialist_agent.as_tool(name=..., description=..., delegate=True)` then `Agent(tools=[...])`.
- Extractor walks `supervisor.messages`, never reads the Supervisor's own final text — only `toolResult` → `content[].json` blocks. For the unified 3-tool supervisor, additionally correlate via `toolUse.name` (walk `toolUse` blocks for `toolUseId -> name` first, then match `toolResult.toolUseId`) rather than taking the first `json` block found, since three different specialists' results can co-occur.
- All `isinstance` defensive guards (message/block/toolResult/content_block) must be preserved verbatim — required by `test_extract_proposal_result_tolerates_malformed_content_blocks`-style tests.

### Bedrock fail-fast → credential-free 503
**Source:** `backend/api.py` lines 80-112 (`map_bedrock_error`), applied at lines 175-186
**Apply to:** the new `/advance` `stage == "ops"` branch — wrap `ops_runner(...)` call in the identical `try/except HTTPException: raise / except Exception as exc: raise HTTPException(503, str(map_bedrock_error(exc)))` shape. No new mapping logic required; reuse the function as-is.

### VERBATIM typed merge (no re-authoring)
**Source:** `backend/api.py` lines 188-206 (proposal/contract merge)
**Apply to:** ops merge — `record.ops = OpsSlice(...)` built directly from the runner's typed result fields, never from Supervisor prose; persist via `store.save(record)`.

### Construction-only offline testability
**Source:** `backend/agents/proposal_contract_agent.py` lines 10-12, `gig_triage_agent.py` lines 9-10
**Apply to:** `build_ops_agent()` — building the Agent must perform NO network call; only invoking it touches Bedrock. This is what lets `test_build_full_supervisor_registers_all_three_tools`-style tests run without AWS credentials.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/fixtures/*.json` + loader | config/utility | file-I/O | No existing fixture directory or JSON-loading utility in this codebase; nearest precedent is inline Python literal test constants (`test_proposal_runner.py` lines 16-20), which is a different mechanism (no file I/O). Build per PRD §10 + D-04 from scratch, keeping it pure-data/no-store-import consistent with every other established pattern here.

## Metadata

**Analog search scope:** `backend/agents/`, `backend/tools/`, `backend/models/`, `backend/api.py`, `backend/tests/`
**Files scanned:** `supervisor.py`, `proposal_runner.py`, `triage_runner.py`, `proposal_contract_agent.py`, `gig_triage_agent.py`, `check_scope_clarity.py`, `draft_proposal.py`, `draft_contract.py`, `placeholder_triage.py`, `api.py`, `engagement_record.py`, `test_single_writer.py`, `test_proposal_runner.py`, `test_proposal_supervisor_wiring.py`
**Pattern extraction date:** 2026-09-08
