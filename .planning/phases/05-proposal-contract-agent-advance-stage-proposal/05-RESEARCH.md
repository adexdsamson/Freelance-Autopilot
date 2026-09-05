# Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal") - Research

**Researched:** 2026-09-05
**Domain:** Strands Agents SDK (mutually-exclusive structured output, agents-as-tools) + FastAPI stage-advance endpoint, extending the Phase-3 (`gsd/phase-03`) foundation
**Confidence:** HIGH on Strands structured-output/agents-as-tools mechanics (source-read against the installed `strands-agents==1.54.0` package this session) and on all Phase-3 code patterns (all files read this session) — MEDIUM on the deterministic `check_scope_clarity` heuristic (no structured `timeline`/`deliverables` fields exist on `JobSlice`, so the gate necessarily infers from free text — a design choice, not a verified fact) — LOW/none on anything requiring a live Bedrock call (sandbox has placeholder AWS creds; not exercised this session, matches Phase 1/3 precedent).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The Proposal-Contract specialist returns ONE strict typed result whose two
  outcomes are **mutually exclusive**: either the happy path (a populated proposal +
  contract + structured payment schedule) OR the escalation path
  (`needs_human_input=true` + a specific `question`, with no populated contract). No single
  response carries both a fully populated contract and `needs_human_input=true` (SC3).
  `needs_human_input`/`question` are **first-class optional fields from the start** so the
  deliberately ambiguous fixture escalates cleanly and never raises a structured-output
  exception (SC2; STATE.md Phase-5 blocker). — **Reversibility:** costly — this schema is
  the contract FastAPI merges and every proposal-stage test asserts against; changing its
  shape later touches the specialist, the merge, and the tests together.

- **D-02:** Mirror Phase 3's `TriageRunner` DI seam exactly with a `ProposalRunner` seam
  (raw record/job in → typed proposal-contract result out). Ship a **deterministic
  default** implementation (template-driven proposal/contract + a deterministic
  scope-clarity gate) so `/advance` is exercisable and **deterministic offline** without
  Bedrock, and a **live supervisor/agent path** selected by a `PROPOSAL_BACKEND` env flag
  (default = deterministic). — **Reversibility:** reversible.

- **D-03:** Build the three PRD §7.2 tools as the ONE source of truth for their rules,
  `@tool`-decorated so they are callable both as plain Python (deterministic path) and
  registered on the specialist Agent (live path) — the same dual-use pattern as
  `backend/tools/placeholder_triage.py`:
  - `check_scope_clarity` — a **deterministic gate** (no LLM) flagging missing budget,
    timeline, or deliverables; fully offline-testable like `kill_switch_check`.
  - `draft_proposal` — a **phased-scope** proposal.
  - `draft_contract` — an SOW with **enumerable deliverables + milestones + payment terms**.
  None of these import the store (single-writer guard, REC-03 — `test_single_writer.py`
  scans `backend/tools/` and `backend/agents/`).

- **D-04:** Wire a **distinct** Proposal-Contract `Agent` instance into a Supervisor via the
  same agents-as-tools shape Phase 3 proved (two distinct Agent instances, observable as
  separate invocations in a live trace). Do **not** prematurely implement ORC-01's full
  three-agent Supervisor (Phase 6) — extend only what the proposal stage needs behind the
  seam. — **Reversibility:** reversible — Phase 6 folds this specialist into the unified
  three-agent Supervisor.

- **D-05:** `POST /engagements/{id}/advance` is the ONLY path that mutates the `proposal`
  and `contract` slices. It: loads the record (404 if unknown); **guards** that triage
  exists and `verdict == "apply"` (otherwise a 4xx); runs the specialist via the
  `ProposalRunner` DI seam; merges the typed result **VERBATIM** into `proposal` (+
  `contract` on the happy path) without the Supervisor re-authoring it; persists via the
  existing `store.save(record)`; returns the updated record. Structure the handler so
  Phase 6 adds `stage="ops"` without a rewrite. Reuse Phase 3's `map_bedrock_error` → 503
  on any Bedrock failure. — **Reversibility:** costly — endpoint shape / status-code
  contract is what Phase 6 and any client build on.

- **D-06:** Produce a **structured** payment schedule (typed milestones — e.g.
  label/amount/due-marker — not free prose) so SC1's "structured payment schedule" is
  machine-checkable and demo-deterministic. `ContractSlice.payment_schedule` (`list[dict]`)
  may be tightened to a typed milestone model. — **Reversibility:** costly — persisted
  record shape; a change is a stored-JSON migration once records exist.

- **D-07:** Offline tests (no creds) MUST pass and verify: (a) deterministic path yields a
  valid proposal + contract + structured payment schedule for a clear-scope apply fixture
  (SC1); (b) a deliberately ambiguous fixture yields `needs_human_input=true` + a specific
  `question` and raises **no** structured-output exception (SC2); (c) mutual exclusivity
  holds (SC3); (d) the merge is FastAPI-only and reaches the record verbatim (SC4); (e)
  `/advance` guards non-apply/unknown engagements; (f) the app + Supervisor +
  Proposal-Contract Agent construct without creds; (g) `/advance` fails fast + readably
  (503, never a raw 500) when the live path raises. The live two-agent Bedrock trace is a
  documented **manual** verification, exactly as in Phases 1 and 3.

### Claude's Discretion

- Module layout (`backend/agents/proposal_contract_agent.py`, `backend/agents/proposal_runner.py`,
  `backend/tools/{draft_proposal,draft_contract,check_scope_clarity}.py` per PRD §12, vs
  consolidating), the exact typed result model name/shape, the precise 4xx code for the
  non-apply guard (409 vs 422), the deterministic template wording, and whether the live
  path extends `build_supervisor()` or uses a stage-scoped builder — all at Claude's
  discretion, consistent with the Phase 3 idioms.

### Deferred Ideas (OUT OF SCOPE)

- Full three-agent Supervisor (ORC-01) — Phase 6.
- `stage="ops"` advancing + formal API-03 completion — Phase 6.
- Ops specialist, scope-creep/invoice tooling, Stage 2–3 fixture set (DEMO-01) — Phase 6.
- LLM-authored proposal/contract prose quality — the live path exists behind the seam; the
  demo runs deterministic.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROP-01 | `draft_proposal` generates a phased-scope proposal for an `apply` engagement | §Code Examples "draft_proposal"; §Architecture Pattern 2 (deterministic composition) |
| PROP-02 | `draft_contract` generates a contract (SOW with enumerable deliverables + milestones + payment terms) | §Code Examples "draft_contract"; §Standard Stack `PaymentMilestone`/`ContractSlice` |
| PROP-03 | A structured payment schedule is produced alongside the contract | §D-06 payment-schedule model (research question 5); `ContractSlice.payment_schedule: list[PaymentMilestone]` |
| PROP-04 | `check_scope_clarity` flags missing budget, timeline, or deliverables, and the agent returns `needs_human_input` + a specific `question` rather than guessing when scope/budget is ambiguous | §Research Question 1 (`ProposalContractResult` mutual-exclusivity schema); §Pitfall 3 verification (source-read, confirms no crash on ambiguous input) |
</phase_requirements>

## Summary

Phase 5 adds one new specialist (Proposal-Contract Agent), one new DI seam
(`ProposalRunner`/`PROPOSAL_BACKEND`), three new dual-use `@tool` functions, and one new
FastAPI endpoint (`POST /engagements/{id}/advance?stage=proposal`) — every one of these has
an exact, already-identified analog in the Phase-3 code this branch is stacked on
(confirmed against `05-PATTERNS.md`'s pattern map, which independently derived the same
file list and mirroring strategy from CONTEXT.md alone). This research adds the parts the
pattern map could not derive from static analysis: **live verification against the
installed `strands-agents==1.54.0` source** of exactly how `structured_output_model`
behaves on validation failure (it does **not** crash — it round-trips a `ToolResult`
error back to the model for a retry, confirmed by reading
`strands/tools/structured_output/structured_output_tool.py` this session), and a concrete,
tested-in-source Pydantic schema for the D-01 mutual-exclusivity requirement.

**Primary recommendation:** Define one flat, all-optional-except-guaranteed
`ProposalContractResult` Pydantic model with a `model_validator(mode="after")` that raises
`ValueError` when the happy-path and escalation-path fields are both/neither populated.
Wire `check_scope_clarity`, `draft_proposal`, `draft_contract` as dual-use `@tool`
functions exactly like `placeholder_kill_switch_check`. Build a **stage-scoped**
`build_proposal_supervisor()` (a *second*, separate supervisor construction function, not
an extension of `build_supervisor()`) wired to *only* the Proposal-Contract specialist —
this sidesteps a real disambiguation problem that a single two-tool supervisor would
introduce (see Research Question 3) while still satisfying D-04's "two distinct Agent
instances" requirement. Mirror `extract_triage_result` verbatim as
`extract_proposal_result`. Add `POST /engagements/{id}/advance` with `stage` as a required
query parameter, a 409 guard for missing/non-apply triage, and `map_bedrock_error` reused
unmodified for 503 fail-fast.

## Architectural Responsibility Map

This project has no browser/CDN tier for this phase (backend-only; the Chrome extension
is Phase 4, out of scope here). Tiers below are recast to this project's actual layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stage-advance routing, request/response validation, 404/409/503 mapping | API (FastAPI `api.py`) | — | Sole writer (REC-03/D-05); owns HTTP contract and status codes |
| Scope-clarity gating, proposal/contract drafting business rules | Tool layer (`backend/tools/*.py`) | — | Deterministic, testable, LLM-independent rule bodies; single source of truth reused by both paths |
| Specialist routing/delegation (which specialist answers this stage) | Agent Orchestration (`backend/agents/supervisor.py`) | — | Agents-as-tools pattern; routes only, never re-authors (D-02/ORC-02) |
| Typed proposal-contract result shape, escalation semantics | Model layer (`backend/models/engagement_record.py`) | API (validates on merge) | Shared schema between Strands `structured_output_model` and the FastAPI merge — one definition, two consumers |
| Engagement Record persistence (read-modify-write) | Storage (`backend/store/*.py`) | API (only caller) | Single-writer boundary; agents/tools never touch it directly |

## Standard Stack

No new external packages are required for this phase — Phase 1 already installed and
pinned everything needed (`strands-agents==1.54.0`, `pydantic>=2.13,<3`, `boto3`,
`fastapi>=0.141,<0.142`, `pytest`/`httpx`), verified this session via
`backend/pyproject.toml` and a live `python3 -m pytest` run (37/37 passing offline).

### Core (already installed — no new install step)

| Library | Version (pinned, `backend/pyproject.toml`) | Purpose in this phase | Why Standard |
|---------|---------|---------|--------------|
| `strands-agents` | `==1.54.0` [VERIFIED: backend/pyproject.toml:7] | `Agent`, `@tool`, `structured_output_model=`, `.as_tool(delegate=True)` for the new specialist | Same pinned version Phase 3 verified; source-read this session confirms the exact mechanics this phase depends on |
| `pydantic` | `>=2.13,<3` [VERIFIED: backend/pyproject.toml:8] | `ProposalContractResult`, `PaymentMilestone`, enriched `ContractSlice` | v2 `model_validator(mode="after")` is the mechanism for D-01's mutual-exclusivity guarantee |
| `fastapi` | `>=0.141,<0.142` [VERIFIED: backend/pyproject.toml:10] | New `/advance` route | Same version already hosting `/capture`/`/engagements/{id}` |
| `boto3` | `>=1.43,<2` [VERIFIED: backend/pyproject.toml:9] | Underlies `BedrockModel` for the live path | Unchanged from Phase 3 |
| `pytest` + `httpx` | dev extra [VERIFIED: backend/pyproject.toml:16-18] | New test files | Unchanged from Phase 3 |

### Supporting

None new.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flat `ProposalContractResult` + `model_validator` | A `Literal`-discriminated union (`HappyResult \| EscalationResult`) | A discriminated union is arguably "more Pydantic-idiomatic," but Strands' `structured_output_model` parameter expects **one** `type[BaseModel]`, not a `Union` — passing a union type is not a documented/verified pattern against the installed SDK (the `Agent(structured_output_model=...)` signature in `agent.py:210` types it as `type[BaseModel] \| None`, singular). The flat model matches `TriageSlice`'s existing style (Phase 3 precedent) and is what Strands' own docs give as the "make the escalation fields first-class optional fields" workaround (Pitfall 3) |
| Stage-scoped `build_proposal_supervisor()` | Extend `build_supervisor()` to carry both `gig_triage_agent` and `proposal_contract_agent` tools | Two tools on one supervisor works for *routing*, but `extract_proposal_result`'s toolResult scan (mirroring `extract_triage_result`) would then need to disambiguate between two tools' `toolResult` blocks by `toolUseId`↔`toolUse.name` cross-reference — extra complexity and a new failure mode not present in the one-tool case. A stage-scoped builder keeps the single-scan `extract_*_result` pattern exactly as proven in Phase 3, with zero risk of picking up the wrong specialist's result |

**Installation:** none — no new packages this phase.

**Version verification:** confirmed live this session:
```bash
$ cd backend && python3 -m pytest -q
37 passed, 1 warning in 2.97s
```
`strands-agents` version confirmed via `pip3 show strands-agents` → `Version: 1.54.0`,
matching the pin.

## Package Legitimacy Audit

**Not applicable — this phase installs no new external packages.** All dependencies
(`strands-agents==1.54.0`, `pydantic`, `boto3`, `fastapi`, `pytest`, `httpx`) were already
vetted and pinned in Phase 1 (`backend/pyproject.toml`, confirmed present and installed
this session). No `package-legitimacy check` run needed; nothing to add to
`requirements.txt`/`pyproject.toml`.

## Architecture Patterns

### System Architecture Diagram

```
POST /engagements/{id}/advance?stage=proposal
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ api.py :: advance()                                              │
│  1. store.get(id) ─────────────────────────► 404 if None         │
│  2. guard: record.triage is None                                 │
│           or record.triage.verdict != "apply" ──► 409             │
│  3. try: result = proposal_runner(record.job)                     │
│     except <botocore/strands exc> ──► map_bedrock_error ──► 503   │
│  4. record.proposal = ProposalSlice(...)          (VERBATIM)      │
│     if not result.needs_human_input:                              │
│         record.contract = ContractSlice(...)      (VERBATIM)      │
│  5. store.save(record)                                            │
│  6. return record                                                  │
└───────────────────────────┬────────────────────────────────────────┘
                             │ proposal_runner(job) — DI seam
                             ▼
        PROPOSAL_BACKEND=placeholder (default)   PROPOSAL_BACKEND=supervisor (manual/live)
        ┌───────────────────────────┐            ┌─────────────────────────────────────┐
        │ _deterministic_proposal_  │            │ _supervisor_proposal_runner          │
        │ runner(job)               │            │  build_proposal_supervisor()         │
        │  1. check_scope_clarity   │            │  supervisor(f"Draft ... {job}")      │
        │     (job.budget,          │            │        │                              │
        │      job.description)     │            │        ▼ .as_tool(delegate=True)      │
        │  2a. if unclear:          │            │  proposal_contract_agent (BedrockModel)│
        │      → escalation result  │            │   tools=[check_scope_clarity,          │
        │  2b. else:                │            │          draft_proposal,               │
        │      draft_proposal(job)  │            │          draft_contract]               │
        │      draft_contract(job,  │            │   structured_output_model=             │
        │        proposal)          │            │      ProposalContractResult            │
        │  3. assemble              │            │        │                              │
        │     ProposalContractResult│            │        ▼ AgentResult.structured_output  │
        │     (model_validator      │            │  extract_proposal_result(               │
        │      enforces D-01)       │            │    supervisor.messages)                 │
        └───────────────────────────┘            │   → reads toolResult{"json":...} block  │
                                                  │   → ProposalContractResult.model_validate│
                                                  └─────────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/
├── agents/
│   ├── proposal_contract_agent.py   # NEW — build_proposal_contract_agent()
│   ├── proposal_runner.py           # NEW — ProposalRunner seam, PROPOSAL_BACKEND
│   └── supervisor.py                # MODIFY — add build_proposal_supervisor() +
│                                     #          extract_proposal_result() (new fns,
│                                     #          build_supervisor() untouched)
├── tools/
│   ├── check_scope_clarity.py       # NEW
│   ├── draft_proposal.py            # NEW
│   └── draft_contract.py            # NEW
├── models/
│   └── engagement_record.py         # MODIFY — PaymentMilestone, tightened
│                                     #          ContractSlice, ProposalContractResult
├── api.py                           # MODIFY — POST /engagements/{id}/advance
└── tests/
    ├── test_proposal_runner.py      # NEW
    ├── test_advance_endpoint.py     # NEW
    └── test_advance_bedrock_failfast.py  # NEW
```

### Pattern 1: Mutually-exclusive structured result (D-01/PROP-04/SC2/SC3)

**What:** One flat Pydantic model with every field `Optional`/defaulted, plus a
`model_validator(mode="after")` that raises when the two outcomes are both/neither
satisfied.

**When to use:** Any Strands specialist whose spec includes an escalation branch
(`needs_human_input`-style) alongside a happy-path payload — this is the documented
workaround for Pitfall 3 ("structured-output exceptions when the LLM wants to ask a
question instead of answering the schema").

**Example (recommended concrete definition, add to `models/engagement_record.py`):**
```python
# Source: pydantic v2 model_validator (self-verified against installed pydantic>=2.13,<3);
# schema shape follows the Strands-documented "escalation fields as first-class Optionals"
# workaround (research/PITFALLS.md Pitfall 3) and mirrors TriageSlice's existing style
# (backend/models/engagement_record.py:25-28).
from pydantic import model_validator

class PaymentMilestone(BaseModel):
    label: str
    amount: float
    due_marker: str  # e.g. "on_signing", "on_delivery", "net_15" — a symbolic marker,
                      # not a calendar date (no signing date exists yet at draft time)


class ProposalContractResult(BaseModel):
    needs_human_input: bool = False
    question: Optional[str] = None
    proposal_text: Optional[str] = None
    contract_text: Optional[str] = None
    payment_schedule: list[PaymentMilestone] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_mutual_exclusivity(self) -> "ProposalContractResult":
        happy_fields_populated = bool(
            self.proposal_text or self.contract_text or self.payment_schedule
        )
        if self.needs_human_input:
            if happy_fields_populated:
                raise ValueError(
                    "needs_human_input=True must not carry a populated proposal_text, "
                    "contract_text, or payment_schedule (SC3)"
                )
            if not self.question:
                raise ValueError("needs_human_input=True requires a non-empty question")
        else:
            if not (self.proposal_text and self.contract_text and self.payment_schedule):
                raise ValueError(
                    "the happy path requires proposal_text, contract_text, and a "
                    "non-empty payment_schedule"
                )
        return self
```

**Why this doesn't crash on the ambiguous fixture (SC2), verified against installed SDK:**
On the **deterministic** path, your own runner code decides up front which branch to
construct (`ProposalContractResult(needs_human_input=True, question=...)` OR the full
happy-path kwargs) — the validator only ever fires as an assertion on your own assembly
logic, never on LLM output, so there is no exception risk on this path at all when the
runner is written correctly (and if it *is* written incorrectly, failing loudly here in a
unit test is exactly what you want).

On the **live** path, `structured_output_model=ProposalContractResult` registers a
`StructuredOutputTool` (source: `strands/tools/structured_output/structured_output_tool.py:107-149`,
read this session). Its `stream()` method wraps model construction in
`try/except ValidationError` — a validator failure (including our `model_validator`
raising `ValueError`, which pydantic wraps as part of `ValidationError`) becomes a
`{"status": "error", ...}` `ToolResult` **fed back to the model as a normal tool error**,
not an exception propagated to Python caller code. The LLM sees the validation error
message and can retry with a corrected shape. This directly refutes the naive fear
("ambiguous input crashes the agent") — the actual risk on the live path is different:
if the model repeatedly fails validation and exhausts its turn budget without ever
emitting a valid shape, `AgentResult.structured_output` stays `None` and
`extract_proposal_result` will raise its own `RuntimeError` (no toolResult json block
found) — a clean, already-tested failure mode (mirrors
`test_extract_triage_result_raises_when_absent`), not a raw crash.

### Pattern 2: Deterministic composition of the three tools (research question 2)

**What:** `_deterministic_proposal_runner(job)` calls the three `@tool`-decorated
functions as **plain Python functions** (the `@tool` decorator preserves normal
callability — verified precedent: `_deterministic_triage_runner` calls
`placeholder_kill_switch_check(job.budget, job.description)` directly, no `Agent`
involved, `backend/agents/triage_runner.py:29-34`).

**Composition order:**
```python
# backend/agents/proposal_runner.py (new)
def _deterministic_proposal_runner(job: JobSlice) -> ProposalContractResult:
    clarity = check_scope_clarity(job.budget, job.description)
    if not clarity["clear"]:
        return ProposalContractResult(
            needs_human_input=True,
            question=clarity["question"],
        )
    proposal = draft_proposal(job.title, job.description, job.budget)
    contract = draft_contract(job.title, job.description, proposal["proposal_text"])
    return ProposalContractResult(
        proposal_text=proposal["proposal_text"],
        contract_text=contract["contract_text"],
        payment_schedule=contract["payment_schedule"],
    )
```

**`check_scope_clarity`'s gate — a keyword-based heuristic (flagged, not verified):**
`JobSlice` (`backend/models/engagement_record.py:18-22`, read this session) has only
`title`, `description`, `budget`, `client_stats` — **no structured `timeline` or
`deliverables` fields**. PRD §7.2/D-03 require flagging "missing budget, timeline, or
deliverables," so timeline/deliverables signals must come from scanning
`job.description` text, the same keyword-scan shape as
`placeholder_kill_switch_check`'s `RED_FLAG_KEYWORDS` (`backend/tools/placeholder_triage.py:30-37`):

```python
# Source: design pattern, NOT verified against any external spec — [ASSUMED], flagged in
# the Assumptions Log below. Structurally identical to the existing verified
# placeholder_kill_switch_check keyword-scan pattern.
TIMELINE_MARKERS = {"week", "weeks", "month", "months", "deadline", "asap", "by ", "days"}
DELIVERABLE_MARKERS = {"deliverable", "milestone", "pages", "wireframe", "revisions", "phase"}

@tool
def check_scope_clarity(budget: float | None, description: str) -> dict:
    """Deterministic gate (no LLM): flags missing budget, timeline, or deliverables
    signals. Returns {"clear": bool, "question": str | None}."""
    lowered = (description or "").lower()
    missing = []
    if budget is None:
        missing.append("budget")
    if not any(marker in lowered for marker in TIMELINE_MARKERS):
        missing.append("timeline")
    if not any(marker in lowered for marker in DELIVERABLE_MARKERS):
        missing.append("deliverables")
    if missing:
        return {
            "clear": False,
            "question": f"Could you clarify the {', '.join(missing)} for this engagement?",
        }
    return {"clear": True, "question": None}
```

**Dual-use confirmed:** the `@tool` decorator preserves plain callability (verified
Phase-3 precedent — the same claim underlies `_deterministic_triage_runner`, which is
already exercised by 37 passing tests this session). No new verification needed; this is
the same mechanism, not a new one.

### Pattern 3: Live path — stage-scoped supervisor, not an extended `build_supervisor()`

**What:** Add a **second**, independent supervisor-construction function
(`build_proposal_supervisor()`) to `backend/agents/supervisor.py`, wired to *only* the
Proposal-Contract specialist — do not add the Proposal-Contract specialist as a second
tool on the existing `build_supervisor()`.

**Why (this is the load-bearing research finding for question 3):** `_AgentAsTool.stream()`
(`strands/agent/_agent_as_tool.py:256-263`, read this session) emits the toolResult json
block whenever `result.structured_output` is truthy — this check runs **unconditionally**,
before the `elif self._delegate:` branch, for *every* registered agent-as-tool. If
`build_supervisor()` carried both `gig_triage_agent` (with `structured_output_model=TriageSlice`)
and `proposal_contract_agent` (with `structured_output_model=ProposalContractResult`)
as two tools, and a caller invoked the supervisor for the proposal stage, the
model *could* call either tool (or both, across turns) — `extract_proposal_result`'s
single toolResult scan (mirroring `extract_triage_result` exactly) would then risk
matching the **wrong** specialist's toolResult block if both fired in the same
conversation, since neither `extract_triage_result` nor its mirror inspect `toolUseId` to
disambiguate by originating tool name. A stage-scoped supervisor with exactly one
registered specialist tool makes this ambiguity structurally impossible — the single-scan
`extract_*_result` pattern stays correct with zero extra disambiguation logic, exactly
matching the already-tested Phase 3 mechanism.

**This still satisfies D-04** ("two distinct Agent instances, observable as separate
invocations") — `build_proposal_supervisor()` is a Supervisor `Agent` distinct from the
`proposal_contract_agent` specialist `Agent`, exactly as `build_supervisor()` +
`build_gig_triage_agent()` are today. It does **not** yet implement ORC-01 (a single
supervisor routing among three specialists) — that consolidation is explicitly Phase 6's
job (D-04's own reversibility note: "Phase 6 folds this specialist into the unified
three-agent Supervisor").

**Example:**
```python
# backend/agents/supervisor.py — ADD, do not modify build_supervisor()/extract_triage_result
def build_proposal_supervisor() -> Agent:
    """Construct (do not invoke) the stage-scoped Supervisor wired to only the
    Proposal-Contract specialist. Mirrors build_supervisor()'s shape exactly
    (D-04) but is a SEPARATE supervisor, not build_supervisor() extended, to
    avoid extract_proposal_result needing cross-tool disambiguation (see
    RESEARCH.md Pattern 3)."""
    proposal_contract_agent = build_proposal_contract_agent()
    proposal_tool = proposal_contract_agent.as_tool(
        name="proposal_contract_agent",
        description=(
            "Draft a phased-scope proposal, an SOW contract with milestones, and a "
            "structured payment schedule for an apply-verdict engagement. Escalate "
            "with needs_human_input + a question if scope/budget is ambiguous — "
            "never guess. Call this whenever a proposal/contract is needed."
        ),
        delegate=True,  # same verified-compatible flag Phase 3 used (BedrockModel.stateful == False)
    )
    return Agent(
        system_prompt=(
            "You route every proposal-drafting request to the proposal_contract_agent "
            "tool. Never answer yourself."
        ),
        tools=[proposal_tool],
    )


def extract_proposal_result(supervisor_messages: list[dict]) -> ProposalContractResult:
    """Mirrors extract_triage_result exactly (single toolResult json scan) —
    safe here because build_proposal_supervisor() registers exactly one
    specialist tool."""
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
                    return ProposalContractResult.model_validate(content_block["json"])
    raise RuntimeError("proposal_contract_agent tool result not found in supervisor trace")
```

`build_proposal_contract_agent()` (new, `backend/agents/proposal_contract_agent.py`)
mirrors `build_gig_triage_agent()` exactly (`backend/agents/gig_triage_agent.py:26-38`,
read this session): same `MODEL_ID`/`REGION` env-var pattern, `tools=[check_scope_clarity,
draft_proposal, draft_contract]`, `structured_output_model=ProposalContractResult`, no
eager network call at construction time (this is what lets D-07(f)'s offline-construction
test pass).

### Pattern 4: `/advance` endpoint (research question 4)

**Stage param — query parameter, not a request body:** `/capture` takes `JobSlice` as a
direct body (no wrapper) and `GET /engagements/{id}` takes only a path param
(`backend/api.py:97-132`, read this session). `/advance` needs no per-call payload for the
proposal stage — everything it needs already lives in the stored record — so a body model
would be pure boilerplate. Recommend `stage: str` as a required query parameter:

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
        # Phase 6 adds an elif stage == "ops": branch here — no rewrite of the
        # guard/merge shape above or below this line.
        raise HTTPException(status_code=400, detail=f"unsupported stage '{stage}'")

    if record.triage is None or record.triage.verdict != "apply":
        raise HTTPException(
            status_code=409,
            detail="engagement has not been apply-triaged; cannot draft a proposal",
        )

    try:
        result = proposal_runner(record.job)  # typed, VERBATIM merge (D-02/ORC-02)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — mirrors /capture's catch-all
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped

    record.proposal = ProposalSlice(
        text=result.proposal_text,
        needs_human_input=result.needs_human_input,
        question=result.question,
    )
    if not result.needs_human_input:
        record.contract = ContractSlice(
            text=result.contract_text,
            payment_schedule=result.payment_schedule,
        )
    store.save(record)
    return record
```

**Why 400 for unsupported stage, 409 for the non-apply guard (two different 4xx, not
one):** these are semantically distinct failures. `stage` is a **request-shape** problem
(the caller asked for a stage this deployment doesn't support yet) — FastAPI's own
convention for "the request itself, independent of resource state, is malformed" is 400
(a raw `str` query param can't use `Literal` validation to auto-404/422 without coupling
the type hint to "only proposal exists so far," which would require a signature rewrite
next phase — exactly what D-05 says to avoid). The triage guard is a **resource-state**
problem (the engagement exists and the request is well-formed, but its current state
doesn't allow this transition) — 409 Conflict is the idiomatic REST status for "valid
request, wrong state," and matches the CONTEXT.md discretion note's own lean ("409 vs
422... recommend 409" per `05-PATTERNS.md`, independently arrived at). 422 is reserved by
FastAPI/Pydantic for request*-body* schema validation failures (as `/capture`'s existing
`test_capture_rejects_malformed_payload` already demonstrates) — reusing it here would
conflate two different failure classes under one status code.

**`store.save()` not `store.create()`:** `/advance` mutates an existing record (loaded via
`store.get`), so use `save`, mirroring D-05's explicit text; `create` is only for
`/capture`'s brand-new record.

**Reuse `map_bedrock_error` unmodified:** already covers `NoCredentialsError`,
`ClientError`, `ModelThrottledException`, `ContextWindowOverflowException`,
`BotoCoreError`, and a catch-all (`backend/api.py:62-94`, read this session) — no new
exception taxonomy needed for the proposal path; the deterministic default path can't
raise any of these types at all (it never touches Bedrock), so this try/except only
activates when `PROPOSAL_BACKEND=supervisor`.

### Anti-Patterns to Avoid

- **Letting the Supervisor's LLM re-author the specialist's proposal/contract text:**
  same anti-pattern as Phase 3 (Pitfalls research, Anti-Pattern 2) — `extract_proposal_result`
  must read the toolResult json block, never the Supervisor's own final-answer text.
- **A single two-tool supervisor for both triage and proposal stages:** see Pattern 3 above
  — structurally introduces a disambiguation risk with no compensating benefit at this
  phase's scope.
- **Deciding scope-clarity from an LLM call instead of a deterministic tool:** would
  reintroduce Pitfall 7 (LLM nondeterminism breaking the repeatable demo) on exactly the
  branch (SC2's escalation trigger) that most needs to fire identically every run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Escalation-vs-happy-path exclusivity | A custom two-endpoint or two-response-type API shape | One Pydantic model + `model_validator(mode="after")` | Matches Strands' own documented workaround for this exact problem (Pitfall 3); keeps one merge site in `/advance` |
| Validating the specialist's live-path output | Manual `json.loads()` + hand-rolled field checks on the Supervisor's raw text | `structured_output_model=` + `AgentResult.structured_output` (verified this session) | Strands already validates and retries against the Pydantic schema inside the tool-calling loop; hand-parsing text reintroduces exactly the "supervisor re-authored it" risk D-02/ORC-02 forbid |
| Extracting the specialist's typed result from a multi-tool trace | A hand-rolled `toolUseId` → `toolUse.name` cross-reference to disambiguate two specialists sharing one supervisor | A stage-scoped supervisor (Pattern 3) so only one tool is ever registered | Avoids introducing correlation logic that doesn't exist anywhere in the verified Phase-3 precedent |

**Key insight:** every "don't hand-roll" here already has a **passing, already-built**
Phase-3 analog (`extract_triage_result`, `TriageRunner`, `placeholder_kill_switch_check`)
that this phase mirrors rather than reinvents — the risk in this phase is drifting from
those proven shapes, not needing a genuinely new mechanism.

## Common Pitfalls

### Pitfall A: Believing structured-output validation failure crashes the live agent (STATE.md Phase-5 blocker)

**What goes wrong:** Teams design the happy-path schema first, treat `needs_human_input`/
`question` as an afterthought, and either (a) never test the ambiguous-fixture path, or
(b) over-engineer defensive `try/except` around the live agent call specifically to catch
a structured-output "crash" that does not actually occur in the installed SDK version.

**Why it happens:** Training-data-era assumptions about "structured output" APIs in other
SDKs (which do sometimes raise on schema mismatch) get applied to Strands without
re-verification.

**How to avoid:** This session's source read of
`strands/tools/structured_output/structured_output_tool.py:107-149` confirms validation
failures become tool-error results fed back to the model, not Python exceptions. The
actual failure mode to guard against is **exhaustion** (the model never successfully
calls the structured-output tool within its turn budget), which surfaces as
`extract_proposal_result` raising its own documented `RuntimeError` — already the correct,
already-tested shape (mirrors `test_extract_triage_result_raises_when_absent`). No new
exception type needs to be added to `map_bedrock_error`.

**Warning signs:** A test asserting `pytest.raises(ValidationError)` around a live agent
call, or a `try/except ValidationError` in `_supervisor_proposal_runner` — both indicate a
misunderstanding of where the validation boundary actually sits.

### Pitfall B: `check_scope_clarity` heuristic drifting from the fixture wording

**What goes wrong:** The keyword-scan gate (Pattern 2) is calibrated against specific test
fixture wording. If the SC1 "clear-scope" fixture and SC2 "ambiguous" fixture are authored
*after* the gate's keyword lists, or vice versa, a wording mismatch causes the wrong
branch to fire and the test silently exercises the wrong code path.

**Why it happens:** the timeline/deliverables signal lives entirely in free-text
`description` (no structured fields exist on `JobSlice` for this — see Pattern 2), so
there is no schema-level guarantee the gate and the fixtures agree.

**How to avoid:** author the SC1 and SC2 fixture `description` strings and the keyword
lists in the same commit/task, and add an explicit regression test asserting the exact
missing-field set the ambiguous fixture should trigger (not just "escalates," but
"escalates citing budget/timeline/deliverables specifically").

**Warning signs:** SC2's test passes by coincidence (e.g. only because `budget=None`
independently triggers it) without the timeline/deliverables keyword paths ever being
exercised — check test coverage of `check_scope_clarity` in isolation, not just through
the full `/advance` round-trip.

### Pitfall C: Forgetting the mutual-exclusivity validator is also a runtime assertion on the deterministic path

**What goes wrong:** Treating the `model_validator` as "only for the live LLM path" and
letting the deterministic runner bypass `ProposalContractResult(...)` construction (e.g.
building a raw `dict` and never running it through the Pydantic model).

**Why it happens:** the deterministic path "already knows" which branch it's building, so
the validator feels redundant.

**How to avoid:** always construct `ProposalContractResult(...)` (not a bare dict) in
`_deterministic_proposal_runner`, even though you "know" it's correct — this is what
makes SC3 machine-checkable rather than merely convention, and it's what a future edit to
`_deterministic_proposal_runner` (e.g. someone adding a new field) gets checked against
for free.

**Warning signs:** `_deterministic_proposal_runner` returns a `dict` that `api.py` then
has to `.model_validate()` itself — this moves the validation boundary out of the runner
and could let a malformed dict reach the merge step in a code path that skips it.

## Code Examples

### `draft_proposal` (PROP-01) — phased-scope, deterministic

```python
# backend/tools/draft_proposal.py (new)
from __future__ import annotations

from strands import tool


@tool
def draft_proposal(title: str, description: str, budget: float | None) -> dict:
    """Draft a phased-scope proposal for a clear-scope apply engagement.
    Deterministic template — no LLM call, same input always produces the
    same output (demo-determinism, Pitfall 7)."""
    budget_line = f"${budget:,.0f}" if budget is not None else "TBD"
    proposal_text = (
        f"Proposal for: {title}\n\n"
        f"Summary: {description.strip()}\n\n"
        f"Approach (phased):\n"
        f"  Phase 1 — Discovery & scoping confirmation\n"
        f"  Phase 2 — Core delivery against the agreed deliverables\n"
        f"  Phase 3 — Revisions & handoff\n\n"
        f"Budget: {budget_line}"
    )
    return {"proposal_text": proposal_text}
```

### `draft_contract` (PROP-02/PROP-03) — SOW + typed milestones

```python
# backend/tools/draft_contract.py (new)
from __future__ import annotations

from strands import tool


@tool
def draft_contract(title: str, description: str, proposal_text: str) -> dict:
    """Draft an SOW contract with enumerable deliverables + milestones, and a
    structured (typed) payment schedule. Deterministic template."""
    contract_text = (
        f"Statement of Work: {title}\n\n"
        f"Deliverables (per proposal):\n"
        f"  1. Discovery & scoping deliverable\n"
        f"  2. Core deliverable per agreed scope\n"
        f"  3. Final revisions & handoff package\n\n"
        f"Payment terms: milestone-based, see payment_schedule."
    )
    payment_schedule = [
        {"label": "On signing", "amount": 0.3, "due_marker": "on_signing"},
        {"label": "On delivery", "amount": 0.5, "due_marker": "on_delivery"},
        {"label": "Final handoff", "amount": 0.2, "due_marker": "net_15"},
    ]
    return {"contract_text": contract_text, "payment_schedule": payment_schedule}
```

*(`amount` shown as a fraction of total budget here for a budget-agnostic template; the
planner may prefer to thread `budget` through and compute absolute amounts — either is
consistent with D-06's "structured, machine-checkable" requirement; the schema shape,
not the arithmetic, is what SC1 checks.)*

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `Agent.structured_output(model, prompt)` / `Agent.structured_output_async(...)` | `Agent(structured_output_model=...)` at construction, or `agent(prompt, structured_output_model=...)` per-call (overrides) | Deprecated in the installed `strands-agents==1.54.0` (confirmed via source read: `agent/agent.py:988-1017` emits a `DeprecationWarning` on the old method) | This phase must use `structured_output_model=` on `Agent(...)` construction (already the pattern Phase 3's `build_gig_triage_agent` uses) — do **not** introduce a call to the deprecated `.structured_output()` method anywhere in the new specialist code |

**Deprecated/outdated:** `Agent.structured_output()`/`.structured_output_async()` — both
present in the installed SDK but explicitly marked deprecated with a warning directing
callers to `structured_output_model=`. CLAUDE.md's own note ("may be superseded") is
confirmed correct this session, not merely suspected.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `check_scope_clarity`'s timeline/deliverables signals should come from a keyword scan of `job.description` (no structured `timeline`/`deliverables` fields exist on `JobSlice`) | Architecture Pattern 2 | If the planner instead expects `JobSlice` to gain new structured fields, this changes the API-01/`/capture` payload shape too (a Phase-3-touching change) — confirm with the user/planner before assuming free-text scanning is acceptable |
| A2 | `PaymentMilestone.amount` is a fraction of budget in the code example (not an absolute dollar figure) | Code Examples | Cosmetic only — either representation satisfies SC1's "structured" requirement; the planner should pick one and keep it consistent across `draft_contract` and any downstream consumer |
| A3 | `due_marker` is a freeform `str` rather than a `Literal[...]` enum | Standard Stack / Pattern 1 | A `Literal` would be more machine-checkable per SC1's spirit but constrains valid values; freeform `str` is safer for a template-driven deterministic default — low risk either way, planner's call |
| A4 | 400 (not 404 or 422) for an unsupported `stage` value | Architecture Pattern 4 | If the planner prefers 404 ("no such stage resource") for consistency with the engagement-not-found case, that's a one-line change with no schema impact — not costly to reverse |

**If this table is empty:** N/A — see rows above; none are load-bearing enough to block
planning, all are cheap to reverse per their own Risk-if-Wrong column.

## Open Questions

1. **Should `PROPOSAL_BACKEND=supervisor`'s exception surface include a `structured_output`
   exhaustion timeout distinct from `RuntimeError("... not found in supervisor trace")`?**
   - What we know: `extract_proposal_result`'s `RuntimeError` already covers "no toolResult
     json block found," which covers both "the model never called the tool" and "the tool
     was called but never validated" cases uniformly.
   - What's unclear: whether `/advance`'s catch-all `except Exception` (which maps to 503
     via `map_bedrock_error`) should special-case this `RuntimeError` with a distinct
     message from actual Bedrock connectivity failures, since it's a different root cause
     (LLM didn't cooperate vs. AWS/network failure) — currently both map to a generic
     "unexpected error contacting Bedrock" 503.
   - Recommendation: leave as one catch-all for Phase 5 (matches D-07(g)'s literal text
     "reuse Phase 3's `map_bedrock_error`"); this is a manual/live-path-only concern with
     no automated test coverage anyway (D-07's live trace is manual-only).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All backend code | ✓ | 3.11 (confirmed: `python3 -m pytest` ran under the venv this session) | — |
| `strands-agents` | Specialist Agent, structured output | ✓ | 1.54.0 (pinned, confirmed via `pip3 show`) | — |
| AWS Bedrock credentials | `PROPOSAL_BACKEND=supervisor` live path only | ✗ (sandbox has placeholder creds, per STATE.md/CONTEXT.md) | — | Deterministic default path (D-02); live path is manual-verification-only (D-07), matching Phases 1 and 3 precedent |
| pytest test suite | All new/existing tests | ✓ | confirmed 37/37 passing this session | — |

**Missing dependencies with no fallback:** none — the one missing dependency (live AWS
Bedrock credentials) already has a documented, in-scope fallback (the deterministic
default path).

**Missing dependencies with fallback:** AWS Bedrock credentials → deterministic
`PROPOSAL_BACKEND` default; live two-agent trace is a documented manual verification step,
not an automated test requirement.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version resolved via `dev` extra in `backend/pyproject.toml`; no pin) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) [VERIFIED: backend/pyproject.toml:20-22] |
| Quick run command | `cd backend && python -m pytest tests/test_proposal_runner.py -x` |
| Full suite command | `cd backend && python -m pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROP-01 | `draft_proposal` produces phased-scope text for a clear-scope job | unit | `python -m pytest tests/test_proposal_runner.py -k draft_proposal -x` | ❌ Wave 0 |
| PROP-02 | `draft_contract` produces SOW text with enumerable deliverables + milestones | unit | `python -m pytest tests/test_proposal_runner.py -k draft_contract -x` | ❌ Wave 0 |
| PROP-03 | Payment schedule is a typed `list[PaymentMilestone]`, not free prose | unit | `python -m pytest tests/test_proposal_runner.py -k payment_schedule -x` | ❌ Wave 0 |
| PROP-04 (SC2) | Ambiguous fixture → `needs_human_input=True` + specific `question`, no exception | unit | `python -m pytest tests/test_proposal_runner.py -k ambiguous -x` | ❌ Wave 0 |
| PROP-04 (SC3) | Mutual exclusivity: never both a populated contract and `needs_human_input=True` | unit | `python -m pytest tests/test_proposal_runner.py -k exclusivity -x` | ❌ Wave 0 |
| D-05 (SC4) | `/advance` merge is FastAPI-only, reaches record verbatim | integration | `python -m pytest tests/test_advance_endpoint.py -x` | ❌ Wave 0 |
| D-05 guard | Unknown engagement → 404; non-apply/no-triage → 409 | integration | `python -m pytest tests/test_advance_endpoint.py -k guard -x` | ❌ Wave 0 |
| D-07(g) | Live-path Bedrock/strands failure → 503, never raw 500 | integration | `python -m pytest tests/test_advance_bedrock_failfast.py -x` | ❌ Wave 0 |
| D-07(f) | App + Supervisor + Proposal-Contract Agent construct without creds | unit | `python -m pytest tests/test_supervisor_wiring.py -k proposal -x` (extend existing file, or a new `test_proposal_supervisor_wiring.py`) | ❌ Wave 0 |
| REC-03 | New agents/tools never import the store | static | `python -m pytest tests/test_single_writer.py -x` | ✅ already covers new files automatically (generic `rglob` scan, no update needed — confirmed by reading the test this session) |

### Sampling Rate

- **Per task commit:** the relevant single test file (`python -m pytest tests/test_<file>.py -x`)
- **Per wave merge:** `cd backend && python -m pytest` (full suite; confirmed baseline 37 passed, 1 warning, 2.97s this session — new phase-5 tests should be added to this same run, no new invocation shape needed)
- **Phase gate:** full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_proposal_runner.py` — covers PROP-01, PROP-02, PROP-03, PROP-04 (SC1/SC2/SC3) at the unit level, unit-testing `_deterministic_proposal_runner` and the three tool functions directly (mirrors `test_triage_runner.py`'s shape exactly)
- [ ] `backend/tests/test_advance_endpoint.py` — covers D-05/SC4 + the 404/409 guards (mirrors `test_capture_endpoint.py`/`test_engagements_endpoint.py`)
- [ ] `backend/tests/test_advance_bedrock_failfast.py` — covers D-07(g) (mirrors `test_capture_bedrock_failfast.py` exactly, swap `get_triage_runner`→`get_proposal_runner`, `/capture`→`/advance`)
- [ ] Extend `backend/tests/test_supervisor_wiring.py` (or add a sibling file) — covers D-07(f)/D-04's "two distinct Agent instances" for the proposal stage-scoped supervisor (mirrors `test_two_distinct_agent_instances_exist`)
- [ ] No new fixture/conftest infrastructure needed — `backend/tests/conftest.py`'s `client`/`file_store` fixtures (tmp-path-bound `FileEngagementStore`) already cover `/advance`'s needs identically to `/capture`'s

## Security Domain

ASVS Level 1 enforcement is active (`security_asvs_level: 1`, confirmed via
`.planning/config.json`). This phase adds no new authentication, session, or external-input
surface beyond what Phase 3 already established (same `EngagementRecord`/`JobSlice`
Pydantic validation boundary, same UUID-typed path param, same store).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single local API key, out of scope per PROJECT.md (unchanged from Phase 3) |
| V3 Session Management | no | Stateless per-request; no session concept in this phase |
| V4 Access Control | no | Single-tenant demo; no per-user authorization boundary introduced |
| V5 Input Validation | yes | Pydantic `BaseModel` validation at every boundary — `EngagementRecord`/`JobSlice` (existing), `ProposalContractResult`/`PaymentMilestone` (new); `engagement_id` remains UUID-typed at the path param (closes path traversal structurally, same as Phase 3, `FileEngagementStore._path()` independently raises `TypeError` on non-UUID) |
| V6 Cryptography | no | No new cryptographic operations introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Raw AWS/Bedrock error message (containing account/credential detail) leaking into an API response | Information Disclosure | Reuse `map_bedrock_error` unmodified (`backend/api.py:62-94`) — already emits only exception type / `Error.Code`, never the raw `Message`; already covered by `test_capture_bedrock_failfast.py`'s assertions (`"top secret detail" not in detail`) — mirror the same assertions in the new `test_advance_bedrock_failfast.py` |
| A crafted `stage` query value probing for an unimplemented/hidden endpoint behavior | Information Disclosure (minor) | The explicit `if stage != "proposal": raise HTTPException(400, ...)` guard (Pattern 4) never branches into unimplemented code — no `ops`-stage code exists yet to accidentally expose |
| An escalation `question` field echoing untrusted job-posting text back to the caller without sanitization | Tampering (stored/reflected content) | `question` is generated by the deterministic template (`check_scope_clarity`) or the LLM, not directly interpolated from raw pasted text without going through the Pydantic `str` type boundary; this is a plain JSON API response (no HTML rendering context in this phase), so XSS is not applicable here — flag for the Chrome-extension-rendering phase (Phase 4, already shipped/independent) if `question` is ever rendered as HTML there |

## Sources

### Primary (HIGH confidence — read directly this session)

- `strands/agent/agent.py` (installed `strands-agents==1.54.0`, `/root/.local/lib/python3.11/site-packages/strands/agent/agent.py`) — `structured_output_model` parameter (constructor + `__call__`/`invoke_async`), deprecated `.structured_output()`/`.structured_output_async()` methods with `DeprecationWarning`
- `strands/agent/_agent_as_tool.py` — `_AgentAsTool.stream()`, confirms `result.structured_output` truthy check runs before the `delegate` branch, emitting `{"json": result.structured_output.model_dump(mode="json")}` as the toolResult content
- `strands/tools/structured_output/structured_output_tool.py` — `StructuredOutputTool.stream()`, confirms `ValidationError` is caught and returned as a tool-error `ToolResult` (fed back to the model), never raised to the Python caller
- `backend/api.py`, `backend/agents/{triage_runner,supervisor,gig_triage_agent}.py`, `backend/tools/placeholder_triage.py`, `backend/models/engagement_record.py`, `backend/store/{engagement_store,file_engagement_store}.py`, `backend/tests/*.py` — all read in full this session
- `backend/pyproject.toml` — pinned dependency versions
- Live `cd backend && python3 -m pytest -q` → `37 passed, 1 warning in 2.97s` (this session)

### Secondary (MEDIUM confidence)

- `.planning/research/PITFALLS.md` Pitfall 3 — the documented Strands workaround for
  escalation-field structured output ("make every field that isn't guaranteed by the
  escalation path Optional") — cross-checked against this session's source read, confirmed
  consistent
- `.planning/research/ARCHITECTURE.md` Pattern 2 — "structured tool contract instead of
  free-text delegation," confirms the VERBATIM-merge design intent predates this phase
- `.planning/phases/05-.../05-PATTERNS.md` — independently derived pattern map (from
  CONTEXT.md alone, no RESEARCH.md available at that time); this research's file-level
  recommendations converge with it exactly, and this research adds the source-verified
  mechanics (structured-output failure behavior, the disambiguation risk behind Pattern 3)
  the pattern-mapper could not derive from static analysis alone

### Tertiary (LOW confidence)

- None — no WebSearch-only claims in this research; every claim above is either read from
  installed source, read from tracked repo files, or explicitly flagged `[ASSUMED]` in the
  Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all versions confirmed via `pyproject.toml` + live `pip3 show`
- Architecture: HIGH — every pattern is either a direct mirror of already-tested Phase-3 code or a source-read confirmation of Strands SDK mechanics
- Pitfalls: HIGH for Pitfall A (source-verified this session, directly resolves the STATE.md Phase-5 blocker) — MEDIUM for Pitfall B (the keyword-heuristic gate itself is a design choice, not a verified external fact)

**Research date:** 2026-09-05
**Valid until:** 30 days (stable — no new external dependencies; risk is drift from the pinned `strands-agents==1.54.0` behavior if the pin changes, not from external API churn)
