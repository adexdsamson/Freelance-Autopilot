# Phase 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike - Research

**Researched:** 2026-09-01
**Domain:** Pydantic v2 data modeling, file-based persistence interface, Strands Agents SDK agents-as-tools smoke test, Bedrock connectivity smoke test
**Confidence:** HIGH on Pydantic/store patterns and package legitimacy; MEDIUM on exact Strands trace-inspection API and Bedrock exception surface (fast-moving SDK, docs thin on failure-mode specifics — verify against the pinned 1.54.0 install at build time, per PITFALLS.md Pitfall 1)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Persistence (REC-02)**
- **D-01:** Use file-based JSON persistence (one JSON file per `engagement_id` under a `data/engagements/` dir) behind an abstract `EngagementStore` interface with `create/get/save` methods. — Reversibility: reversible — SQLite or AgentCore Memory can implement the same interface later without touching callers.
- **D-02:** The store interface is the ONLY persistence seam; the concrete file store is swappable via a single construction point (dependency-injected into FastAPI). This is what lets Phase 8 (AgentCore) be a config change, not a rewrite.

**Engagement Record schema (REC-01)**
- **D-03:** Model the Engagement Record as Pydantic v2 `BaseModel`s exactly matching PRD §6.2 (engagement_id, job, triage, proposal, contract, ops slices), with each stage slice optional/defaulted so a freshly-captured record is valid before later stages run. — Reversibility: costly — the shape is a shared contract between FastAPI I/O, Strands `structured_output()`, and every later phase; changing field names later touches all specialists.
- **D-04:** `engagement_id` is a server-generated UUID (uuid4) assigned at creation.

**Single-writer discipline (REC-03)**
- **D-05:** Only FastAPI (the API layer) calls `EngagementStore.save`. Agents/tools return typed data; the API merges it into the record. Enforce with a module boundary + a test asserting no agent/tool module imports the store. — Reversibility: costly — this is the core determinism/architecture guarantee the judging narrative rests on.

**Strands + Bedrock wiring (ORC-03)**
- **D-06:** Pin `strands-agents` (verified latest 1.54.0) and construct an explicit `BedrockModel(model_id=..., region_name=...)` — never rely on the bare-string model default — so model id and region are visible in code. Model id/region come from environment variables with documented defaults (e.g. `BEDROCK_MODEL_ID`, `AWS_REGION`).
- **D-07:** Use the **agents-as-tools** pattern (specialist `Agent` wrapped in an `@tool` function, passed into the supervisor's `tools=[...]`) — NOT Swarm (non-deterministic) or Graph (overkill). The Phase 1 smoke test builds a throwaway 2-agent version to confirm the pattern and independent tool-call traces.
- **D-08:** The Bedrock connectivity smoke test must **fail fast with a readable, diagnosable error** when credentials/region/model access are missing (this environment may lack AWS credentials). Do not hard-crash the whole app; surface a clear message. The smoke test is a standalone script, not part of the API's import path.

### Claude's Discretion
- Project/package layout under `backend/` (module names, whether to use a `src/` layout), test framework wiring (pytest + httpx), and the exact env-var names/defaults — planner/executor may choose idiomatic conventions consistent with the STACK research.

### Deferred Ideas (OUT OF SCOPE)
- SQLite persistence backend — deferred; file JSON is sufficient for the demo, and the interface makes SQLite a later drop-in.
- AgentCore Memory persistence — Phase 8 (optional, cut-first).
- No real specialist agent, tool logic, HTTP endpoint, or extension work — those are later phases. The Strands/Bedrock work here is a throwaway smoke test, not production agent code.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REC-01 | A single Pydantic-typed Engagement Record models job, triage, proposal, contract, and ops slices per the PRD 6.2 shape. | §"Engagement Record Model" below gives the exact PRD §6.2 field shape translated to Pydantic v2, with every stage slice Optional per D-03/Pitfall 3's Optional-fields lesson. |
| REC-02 | An Engagement Record is persisted per engagement to a durable store (file-based JSON) behind a store interface. | §"EngagementStore Interface" gives the abstract base class + file implementation, atomic-write pattern, and directory layout (`data/engagements/{id}.json`). |
| REC-03 | FastAPI is the sole writer that merges each specialist agent's typed output into the Engagement Record. | §"Single-Writer Enforcement Test" gives a concrete AST-based import-graph test asserting no module under `agents/`/`tools/` imports `store`. |
| ORC-03 | Claude on Amazon Bedrock is wired as the Strands model provider with an explicit model id and region. | §"BedrockModel Wiring" and §"Bedrock Connectivity Smoke Test" give verified constructor args, region resolution order, and the exception types to catch for fail-fast behavior. |
</phase_requirements>

## Summary

This phase has two independent halves that share nothing but a Pydantic schema convention: (1) a data-modeling/persistence half (REC-01/02/03) that is ordinary, low-risk Pydantic v2 + file-I/O work, and (2) a genuinely uncertain SDK-verification half (ORC-03) that must prove the Strands agents-as-tools pattern and Bedrock connectivity actually work against the pinned `strands-agents==1.54.0`, not against training-data assumptions (PITFALLS.md Pitfall 1). Both halves are throwaway-safe in the sense that D-08 explicitly says the Bedrock/Strands smoke test is a standalone script excluded from the API's import path — a missing/invalid AWS credential in this environment (confirmed present below) must not block the phase from being called "done."

The Engagement Record model should be built as nested Pydantic v2 `BaseModel`s mirroring PRD §6.2 exactly, with every stage slice (`triage`, `proposal`, `contract`, `ops`) `Optional[...] = None` so a freshly-created record (job only) validates immediately — this is the same "Optional-except-guaranteed" schema discipline PITFALLS.md Pitfall 3 requires for the Proposal-Contract Agent later, applied here from the start. The `EngagementStore` must be an `abc.ABC` with `create`/`get`/`save` methods, and the concrete `FileEngagementStore` implementation writes one JSON file per `engagement_id` under `data/engagements/`, using write-to-temp-then-rename for atomicity. The single-writer rule (REC-03) is enforced by a static/import-graph test (AST-based grep-equivalent), not a runtime check — cheaper, deterministic, and catches the violation at test time rather than demo time.

For the Strands/Bedrock half: the verified agents-as-tools shapes are (a) wrap a specialist `Agent` in a plain `@tool`-decorated function that constructs the agent internally and returns `str(agent(...))`, or (b) pass a specialist `Agent` instance directly into the supervisor's `tools=[...]` list, or (c) call `specialist.as_tool(name=..., description=...)` for explicit naming — CONTEXT.md D-07 locks in shape (a)/(c) (the `@tool`-wrapped or `.as_tool()` form), not bare list inclusion, so the wiring is visible and named in code. To prove independent tool-call traces (the core judged risk per PITFALLS.md Pitfall 4), inspect `agent.messages` (full message history including `tool_use`/`tool_result` blocks — the eventual specialist invocation is *not* the same object as a flat single-agent trace) and `result.metrics.tool_metrics` (per-tool call counts) on the supervisor's result after calling it. `BedrockModel` construction is `BedrockModel(model_id=..., region_name=...)`; construction itself does not validate credentials or model access — those errors only surface on the first actual `invoke_model` call, so the smoke test must actually call the model (a trivial one-line prompt), not just construct the object, and must catch `botocore.exceptions.NoCredentialsError` and `botocore.exceptions.ClientError` (inspecting `e.response["Error"]["Code"]` for `AccessDeniedException`/`UnrecognizedClientException`/`ValidationException`) separately from generic exceptions, printing a readable diagnostic and exiting non-zero rather than raising a raw traceback.

**Primary recommendation:** Build the Pydantic model + file store + single-writer test first (fully offline, zero AWS dependency, verifiable by `pytest` alone); build the Strands/Bedrock smoke test as a separate standalone script under `backend/scripts/` that is allowed to fail with a clean diagnostic message if AWS credentials in this environment are invalid (they are — see Environment Availability) — do not let Bedrock's real-world unavailability here block REC-01/02/03 from being verified.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Engagement Record schema (Pydantic model) | API / Backend | — | Pure data-shape contract; no client/browser involvement in this phase |
| Engagement Record persistence (file JSON store) | Database / Storage | API / Backend | The store is a storage-tier concern accessed only through the backend-tier interface; FastAPI (not yet built as endpoints in this phase, but its layer) owns the only write path |
| Single-writer enforcement | API / Backend | — | A structural/test-time constraint on the backend's own module graph, not runtime-observable from any other tier |
| Strands supervisor + specialist wiring (throwaway) | API / Backend | — | In-process Python object graph inside the eventual FastAPI process; no HTTP surface exists yet in this phase |
| Bedrock model provider connectivity | API / Backend | External Service (AWS Bedrock) | `BedrockModel` is backend-tier code; Bedrock itself is an external managed service reached over the network via boto3 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `strands-agents` | 1.54.0 [VERIFIED: PyPI project page + `pip index versions strands-agents`] | Core agent framework — `Agent`, `@tool`, `BedrockModel` | Official AWS-sponsored SDK; this phase's whole purpose is verifying it against the pinned version, per D-06 |
| `pydantic` | 2.13.5 [VERIFIED: `pip index versions pydantic`, current at research time] | Engagement Record schema, nested stage-slice models | Pydantic v2 is FastAPI's default and Strands' `structured_output()` schema mechanism; shared model definition serves both later |
| `boto3` | 1.43.85 [VERIFIED: `pip index versions boto3`, current at research time] | Underlying AWS SDK `BedrockModel` uses for Bedrock Runtime calls; also the source of the exception types the smoke test must catch | Pulled in transitively by `strands-agents`; pin explicitly for direct `botocore.exceptions` imports in the smoke test |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | latest [ASSUMED — not independently version-pinned this session; well-established, low-risk] | Test runner for the Pydantic model, store, and single-writer import-graph tests | Always, for this phase's verification |
| `python-dotenv` | latest [ASSUMED] | Load `BEDROCK_MODEL_ID`/`AWS_REGION` env-var defaults from a local `.env` for the smoke test | Optional convenience; only if the team wants `.env`-driven config for the standalone script — not required, `os.environ.get(...)` alone works |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File-based JSON `EngagementStore` | SQLite-backed store | Deferred per CONTEXT.md — same interface makes this a later drop-in; not needed for this phase's throughput (single local demo) |
| AST-based import-graph test for single-writer rule | Runtime monkeypatch / mock assertion that `store.save` is only called from `api.*` call stacks | Runtime approach requires the API layer to exist first (it doesn't yet in Phase 1); static analysis works today against just `models/`, `store/`, and placeholder `agents/`/`tools/` packages |
| `@tool`-wrapped specialist Agent (D-07's locked shape) | Bare `tools=[specialist_agent]` list inclusion | Docs show both work; the `@tool`/`.as_tool()` forms make the wiring's *name* and *description* explicit in code, which matters for the "genuine multi-agent visible in code" judging criterion this project is scored on (ARCHITECTURE.md) |

**Installation:**
```bash
pip install "strands-agents==1.54.0" "pydantic>=2.13,<3" "boto3>=1.43,<2" pytest
```

**Version verification:** Verified directly this session via `pip index versions <pkg>` against the live PyPI index (see Package Legitimacy Audit below) — not from training memory. `pip index` is an experimental pip command; if unavailable in the executor's environment, fall back to `pip install <pkg>==` (which lists available versions in its error output) or the PyPI JSON API (`https://pypi.org/pypi/<pkg>/json`).

## Package Legitimacy Audit

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------------------|-----------|--------------|---------|-------------|
| `strands-agents` | PyPI | latest 1.54.0, 2026-08-27; continuous history back to 0.0.1 [VERIFIED: `pip index versions strands-agents`] | metric unavailable in this sandbox (seam returned `unknown-downloads`) | `github.com/strands-agents/harness-sdk` (official org; repo renamed from `sdk-python`, confirmed via PyPI project-links fetch) | SUS (seam) → **OK** (overridden) | Approved — seam's `too-new`/`unknown-downloads` signals are a sandbox network limitation (download-stats API unreachable), not evidence of illegitimacy; long continuous version history under the official `strands-agents` GitHub org (matching STACK.md/ARCHITECTURE.md sources) confirms legitimacy |
| `pydantic` | PyPI | latest 2.13.5, continuous history back to 0.0.1 [VERIFIED: `pip index versions pydantic`] | metric unavailable in this sandbox | `github.com/pydantic/pydantic` | SUS (seam) → **OK** (overridden) | Approved — extremely well-established package; SUS driven by the same sandbox download-stats gap, not a real risk signal |
| `boto3` | PyPI | latest 1.43.85, continuous history | metric unavailable in this sandbox | `github.com/boto/boto3` | SUS (seam) → **OK** (overridden) | Approved — official AWS SDK, same sandbox limitation |
| `fastapi` | PyPI | present, `unknown-downloads` only (not `too-new`) | metric unavailable | `github.com/fastapi/fastapi` | SUS (seam) → **OK** (overridden) | Approved — used only as a future dependency reference in this phase (no FastAPI code required yet per phase scope) |
| `pytest` | PyPI | present, `unknown-downloads` only | metric unavailable | `github.com/pytest-dev/pytest` | SUS (seam) → **OK** (overridden) | Approved |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** all five packages above were flagged `SUS` by the `package-legitimacy check` seam, but every flag traces to the same two signals — `too-new` (the *latest release date*, not package age — irrelevant for actively-maintained software) and `unknown-downloads` (the seam's download-stats fetch failed in this sandboxed network, returning `null` rather than a real low number). All five are top-tier, official-org packages with decades/years of combined history confirmed via `pip index versions` (showing hundreds of prior releases each) and PyPI project-link verification. **Recommendation to planner: no `checkpoint:human-verify` gate is needed for these five** — the SUS signal here is a diagnostic-tooling gap in this environment, not a real supply-chain risk. If the executor's environment can reach the downloads-stats API, re-running the check there should return `OK` directly.

## Architecture Patterns

### System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│  THROWAWAY SMOKE TEST (backend/scripts/, NOT imported by api.py)│
│                                                                  │
│  smoke_test_agents_as_tools.py                                  │
│    supervisor = Agent(tools=[specialist_tool])  ──calls──▶      │
│    supervisor("do the specialist task")                         │
│         │                                                       │
│         ▼ tool-calling loop picks specialist_tool                │
│    @tool specialist_tool(...)                                   │
│         │ constructs + calls its own Agent(...)                 │
│         ▼                                                       │
│    specialist Agent ──▶ BedrockModel ──▶ AWS Bedrock Runtime     │
│         │                                                       │
│         ▼ returns str(specialist_response)                      │
│    supervisor receives tool result, produces final AgentResult  │
│         │                                                       │
│         ▼ inspect result.messages / result.metrics.tool_metrics │
│    assert: at least one tool_use block for specialist_tool,      │
│            supervisor's own AgentResult reasoning is distinct    │
│            from a single flat single-agent trace                │
│                                                                  │
│  smoke_test_bedrock_connectivity.py                              │
│    BedrockModel(model_id=env, region_name=env) ──▶ Agent(model=) │
│    agent("ping")  ── try/except NoCredentialsError/ClientError   │
│         │                                                       │
│         ├─ success ──▶ print "Bedrock OK", exit 0                │
│         └─ failure ──▶ print readable diagnosis, exit 1           │
│                        (never raises a raw traceback)             │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  PERSISTENT-CONTRACT HALF (backend/, imported by later phases)  │
│                                                                  │
│  models/engagement_record.py  (Pydantic v2, PRD §6.2 shape)      │
│         │ produced/consumed by                                  │
│         ▼                                                       │
│  store/engagement_store.py                                       │
│    EngagementStore(ABC): create() / get(id) / save(id, record)   │
│         │ implemented by                                        │
│         ▼                                                       │
│  store/file_engagement_store.py                                  │
│    FileEngagementStore: data/engagements/{id}.json                │
│         (atomic write: tmp file + os.replace)                     │
│                                                                  │
│  tests/test_single_writer.py                                     │
│    AST-walks agents/*.py and tools/*.py                          │
│    asserts no `import store` / `from store import ...`            │
└────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/
├── models/
│   ├── __init__.py
│   └── engagement_record.py     # EngagementRecord + Job/Triage/Proposal/Contract/Ops slice models
├── store/
│   ├── __init__.py
│   ├── engagement_store.py      # abstract EngagementStore(ABC): create/get/save
│   └── file_engagement_store.py # concrete FileEngagementStore
├── agents/                      # placeholder package this phase (empty __init__.py) —
│   └── __init__.py              # real specialist Agents arrive in Phase 2+; exists now so the
│                                 # single-writer test has a real target directory to scan
├── tools/
│   └── __init__.py              # same placeholder purpose as agents/
├── scripts/
│   ├── smoke_test_agents_as_tools.py    # throwaway 2-agent Strands smoke test (D-07)
│   └── smoke_test_bedrock_connectivity.py  # Bedrock fail-fast smoke test (D-08)
├── data/
│   └── engagements/             # runtime JSON files (gitignored)
├── tests/
│   ├── test_engagement_record.py
│   ├── test_file_engagement_store.py
│   └── test_single_writer.py    # import-graph check enforcing REC-03
└── requirements.txt
```

### Structure Rationale

- **`scripts/` is deliberately outside the package import graph FastAPI will eventually use.** D-08 requires the Bedrock smoke test to be "a standalone script, not part of the API's import path" — placing it in `scripts/` (invoked with `python -m backend.scripts.smoke_test_bedrock_connectivity` or as a direct script) rather than `backend/api.py`-adjacent guarantees `pytest`/`uvicorn` never import it, so a missing/invalid AWS credential (confirmed present in this environment, see Environment Availability) can never break the rest of the test suite or the eventual app boot.
- **`agents/` and `tools/` exist as empty placeholder packages in this phase**, not because Phase 1 builds real specialists (it explicitly does not — CONTEXT.md's Phase Boundary), but because the single-writer test (REC-03) needs a real directory to scan; creating it now with a docstring-only `__init__.py` gives Phase 2+ a pre-verified boundary to build inside without needing to re-derive the test's scan path.
- **`store/engagement_store.py` (interface) and `store/file_engagement_store.py` (implementation) are separate files**, not one — this makes the D-02 "single swappable construction point" concrete: only one line of caller code (a factory function or constant) ever names `FileEngagementStore`, and swapping to a SQLite or AgentCore-backed store later is a one-file addition plus a one-line change at that construction point, never a change to `models/` or any future `agents/`/`tools/` code.

### Pattern 1: Optional-stage-slice Engagement Record (Pydantic v2)

**What:** Every stage slice (`triage`, `proposal`, `contract`, `ops`) on the top-level `EngagementRecord` is `Optional[XxxSlice] = None`, never a required field with defaulted sub-fields. `job` is present at creation (required), everything else starts `None` and is populated only when that stage actually runs.
**When to use:** Always for this model — a freshly-`POST /capture`-created record (Phase 3, not this phase, but the schema is designed here) must validate with only `job` populated; a Pydantic model that requires `triage: TriageSlice` at construction would force fabricating fake triage data just to satisfy the schema.
**Example:**
```python
# models/engagement_record.py
from __future__ import annotations
from typing import Optional, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class JobSlice(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    client_stats: Optional[dict] = None

class TriageSlice(BaseModel):
    verdict: Literal["apply", "skip"]
    score: float
    reasoning: str

class ProposalSlice(BaseModel):
    text: Optional[str] = None
    needs_human_input: bool = False
    question: Optional[str] = None

class ContractSlice(BaseModel):
    text: Optional[str] = None
    payment_schedule: list[dict] = Field(default_factory=list)

class OpsSlice(BaseModel):
    status_updates: list[dict] = Field(default_factory=list)
    scope_creep_flags: list[dict] = Field(default_factory=list)
    invoice_flags: list[dict] = Field(default_factory=list)

class EngagementRecord(BaseModel):
    engagement_id: UUID = Field(default_factory=uuid4)
    job: JobSlice
    triage: Optional[TriageSlice] = None
    proposal: Optional[ProposalSlice] = None
    contract: Optional[ContractSlice] = None
    ops: Optional[OpsSlice] = None
```
This directly implements D-04 (`engagement_id` server-generated via `uuid4`, here as a Pydantic `default_factory`) and D-03 (every later stage slice `Optional`). Note `ProposalSlice.text`/`.question` are also individually `Optional` inside the slice itself — this is the same discipline PITFALLS.md Pitfall 3 requires for the real Proposal-Contract Agent later (an "either complete deliverable OR escalation" branch), applied to the container schema now so later phases don't have to retrofit it.

### Pattern 2: Abstract store + single concrete implementation (D-01/D-02)

**What:** An `abc.ABC` subclass defines `create`/`get`/`save`; exactly one concrete class (`FileEngagementStore`) implements it in this phase.
**When to use:** Always — this is the seam every later phase (API, specialists, Phase 8 AgentCore) builds against.
**Example:**
```python
# store/engagement_store.py
from abc import ABC, abstractmethod
from uuid import UUID
from models.engagement_record import EngagementRecord

class EngagementStore(ABC):
    @abstractmethod
    def create(self, record: EngagementRecord) -> EngagementRecord: ...

    @abstractmethod
    def get(self, engagement_id: UUID) -> EngagementRecord | None: ...

    @abstractmethod
    def save(self, record: EngagementRecord) -> None: ...
```
```python
# store/file_engagement_store.py
import json
import os
from pathlib import Path
from uuid import UUID
from models.engagement_record import EngagementRecord
from store.engagement_store import EngagementStore

class FileEngagementStore(EngagementStore):
    def __init__(self, base_dir: Path = Path("data/engagements")):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, engagement_id: UUID) -> Path:
        return self.base_dir / f"{engagement_id}.json"

    def create(self, record: EngagementRecord) -> EngagementRecord:
        self.save(record)
        return record

    def get(self, engagement_id: UUID) -> EngagementRecord | None:
        path = self._path(engagement_id)
        if not path.exists():
            return None
        return EngagementRecord.model_validate_json(path.read_text())

    def save(self, record: EngagementRecord) -> None:
        path = self._path(record.engagement_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(record.model_dump_json(indent=2))
        os.replace(tmp_path, path)  # atomic on POSIX
```
`model_dump_json`/`model_validate_json` are Pydantic v2 methods (not the v1 `.json()`/`.parse_raw()`); this is a load-bearing detail since STACK.md flags "don't mix Pydantic v1 model definitions in with Strands' `structured_output()` calls, which expect standard Pydantic v2 semantics" — using v2-native serialization here from the start keeps the model consistent with what Strands will expect in later phases. `os.replace` after writing to a `.tmp` file avoids a torn/partial JSON file if the process is killed mid-write — cheap insurance for a demo that gets re-run repeatedly.

### Pattern 3: Agents-as-tools smoke test — three verified wiring shapes

**What:** Strands docs [CITED: strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/] show three ways to expose a specialist `Agent` to a supervisor's `tools=[...]`:
1. `@tool`-decorated function that constructs and calls its own `Agent` internally, returning `str(agent(query))`.
2. Passing the specialist `Agent` instance directly as a list item: `tools=[specialist_agent]`.
3. `specialist_agent.as_tool(name=..., description=...)` for explicit control over the tool's presented name/description.

D-07 locks in shape 1 or 3 (an explicitly `@tool`-wrapped or `.as_tool()`-named specialist) rather than shape 2, because bare list inclusion doesn't give the tool a docstring-derived description under your control — for a throwaway smoke test this doesn't matter functionally, but matching the locked pattern here means the real specialists in Phase 2+ inherit an already-proven wiring shape.

**Example (throwaway smoke test, per D-07/D-08):**
```python
# backend/scripts/smoke_test_agents_as_tools.py
"""Throwaway spike: prove Strands agents-as-tools wiring + independent tool-call
traces work against the pinned strands-agents==1.54.0. NOT imported by api.py."""
from strands import Agent, tool

@tool
def echo_specialist(message: str) -> str:
    """A throwaway specialist agent that echoes back a structured acknowledgment.
    Call this whenever the supervisor needs the echo specialist's response."""
    specialist = Agent(system_prompt="You are a specialist. Reply with exactly: SPECIALIST_ACK: <message>")
    response = specialist(message)
    return str(response)

def main() -> None:
    supervisor = Agent(
        system_prompt="You route every request to the echo_specialist tool. Never answer yourself.",
        tools=[echo_specialist],
    )
    result = supervisor("please process: hello world")

    # Verification: prove the specialist tool was actually invoked, not just
    # answered inline by the supervisor's own model.
    tool_calls = [m for m in supervisor.messages if m.get("role") == "assistant"
                  for block in m.get("content", []) if isinstance(block, dict) and "toolUse" in block]
    assert tool_calls, "Supervisor never invoked a tool — check tools=[...] wiring"
    assert "echo_specialist" in str(result.metrics.tool_metrics), "echo_specialist tool call not recorded in metrics"
    print("PASS: agents-as-tools wiring confirmed, tool call recorded in trace")
    print(f"Final result: {result}")

if __name__ == "__main__":
    main()
```
**Trace verification detail [CITED: strandsagents.com/docs/user-guide/observability-evaluation/metrics/, MEDIUM confidence — inspect the exact shape of `agent.messages` and `result.metrics.tool_metrics` against the installed 1.54.0 at build time, since the docs page shown in this research did not include a direct code sample for this exact assertion]:** `AgentResult.metrics` (an `EventLoopMetrics` instance) exposes `tool_metrics` (per-tool call counts/timings), `accumulated_usage` (token counts), and `cycle_durations`. Separately, `Agent.messages` holds the full conversation/tool-call message history (`tool_use`/`tool_result` content blocks per Strands' Bedrock-native message format), which is the more directly inspectable evidence that the specialist's tool was actually called rather than the supervisor's own model free-answering. **Verify the exact key names (`toolUse` vs `tool_use`, dict vs typed object) against the installed SDK version's actual runtime output before writing the assertion** — this is exactly the kind of guessed-API risk PITFALLS.md Pitfall 1 warns about; print `supervisor.messages` and `result.metrics.tool_metrics` once during development to confirm the real shape, then write the assertion against what you observe.

### Pattern 4: BedrockModel wiring + fail-fast connectivity smoke test

**What:** `BedrockModel(model_id=..., region_name=...)` is constructed once; construction itself performs no network call and raises no credential/access errors — those only surface when the model is actually invoked (i.e., inside `agent("...")`).
**When to use:** Always for this project (D-06) — never pass a bare model-id string to `Agent(model="...")`.
**Example:**
```python
# backend/scripts/smoke_test_bedrock_connectivity.py
"""Throwaway spike: prove Bedrock connectivity works, or fail fast with a
readable diagnosis. Standalone script — never imported by api.py (D-08)."""
import os
import sys
from botocore.exceptions import NoCredentialsError, ClientError, EndpointConnectionError
from strands import Agent
from strands.models import BedrockModel

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")

def main() -> int:
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION)
    agent = Agent(model=model)
    try:
        result = agent("Reply with exactly: PONG")
        print(f"PASS: Bedrock reachable in {REGION} with model {MODEL_ID}")
        print(f"Response: {result}")
        return 0
    except NoCredentialsError:
        print(f"FAIL: no AWS credentials found. Run `aws configure` or export "
              f"AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN.", file=sys.stderr)
        return 1
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "Unknown")
        msg = e.response.get("Error", {}).get("Message", str(e))
        if code == "AccessDeniedException":
            print(f"FAIL: credentials valid but no Bedrock model access for "
                  f"{MODEL_ID} in {REGION}. Enable it in the Bedrock console's "
                  f"'Model access' page for this account/region.", file=sys.stderr)
        elif code == "UnrecognizedClientException":
            print(f"FAIL: AWS credentials present but invalid/expired "
                  f"(UnrecognizedClientException). Check AWS_ACCESS_KEY_ID/"
                  f"AWS_SECRET_ACCESS_KEY are current.", file=sys.stderr)
        elif code == "ValidationException":
            print(f"FAIL: ValidationException — likely wrong model id format "
                  f"for {REGION} (bare foundation-model id vs. required "
                  f"inference-profile id, e.g. 'us.anthropic...'). Message: {msg}", file=sys.stderr)
        else:
            print(f"FAIL: Bedrock ClientError [{code}]: {msg}", file=sys.stderr)
        return 1
    except EndpointConnectionError as e:
        print(f"FAIL: could not reach the Bedrock endpoint in {REGION} "
              f"(network/DNS issue): {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```
**Exception types to catch** [CITED: botocore.exceptions documentation, verified via web search against multiple AWS/community sources — MEDIUM confidence, standard/stable botocore API surface]:
- `botocore.exceptions.NoCredentialsError` — no credentials located anywhere in the chain.
- `botocore.exceptions.ClientError` — AWS returned an error; inspect `e.response["Error"]["Code"]`. Observed codes relevant here: `AccessDeniedException` (valid creds, no model access), `UnrecognizedClientException` (invalid/expired access key or secret — "the security token included in the request is invalid"), `ValidationException` (bad model id / region mismatch, e.g. bare FM id instead of an inference-profile id).
- `botocore.exceptions.EndpointConnectionError` — network/DNS failure reaching the regional Bedrock endpoint.
- **Do not catch bare `Exception`** as the primary strategy — catching the three types above by name and printing their specific remediation is what makes the error "readable and diagnosable" per D-08, versus a generic caught-and-swallowed failure.

### Anti-Patterns to Avoid
- **Asserting Bedrock succeeded without actually invoking the model:** Constructing `BedrockModel(...)` and `Agent(model=...)` without calling `agent(...)` proves nothing — credential/access errors only surface on the real API call. The smoke test must make one real (cheap) call.
- **Catching bare `Exception` in the Bedrock smoke test:** Satisfies "doesn't crash" but fails "readable, diagnosable error" (D-08) — always branch on `NoCredentialsError`/`ClientError.response["Error"]["Code"]`/`EndpointConnectionError` first, with a generic catch-all only as the final fallback.
- **Skipping the trace-inspection assertion in the agents-as-tools smoke test:** Printing `result` and eyeballing that it "looks like" the specialist answered is not proof — PITFALLS.md Pitfall 4's whole point is that a single mega-agent can produce output that *looks* multi-agent. The smoke test must assert on `agent.messages`/`result.metrics.tool_metrics`, not just on the final text.
- **Building the file store without atomic writes:** Writing `record.model_dump_json()` directly to the final path risks a torn JSON file if interrupted mid-write during repeated demo reruns; always write-to-temp-then-`os.replace`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Validating the Engagement Record's JSON shape on load | Custom JSON schema validator / manual `dict` key checks | `EngagementRecord.model_validate_json(path.read_text())` (Pydantic v2) | Pydantic v2 already does full type/shape validation with clear error messages; hand-rolling duplicates it with worse errors |
| Detecting whether a module imports another module | Regex-based text search over file contents (`grep "from store"`) | Python's `ast` module: parse each file, walk `Import`/`ImportFrom` nodes, check module names | AST parsing correctly handles aliased imports (`import store as s`), multi-line imports, and comments/strings that merely *mention* "store" without importing it — a `grep` can false-positive on a docstring or false-negative on `importlib.import_module("store")` |
| Bedrock credential/region resolution | Custom env-var-reading wrapper around boto3 | `BedrockModel(region_name=..., boto_session=...)` + the standard boto3 credential chain | Strands already delegates to boto3's well-tested chain (env vars → shared config → instance role); a custom wrapper adds a second, divergent resolution path that can disagree with boto3's own |

**Key insight:** Both hand-roll traps in this phase (JSON validation, import detection) are cases where a general-purpose, already-imported library (`pydantic`, `ast`) does the job in fewer lines and with better failure modes than bespoke string/regex logic — there is no domain-specific reason to avoid them here.

## Runtime State Inventory

Not applicable — this is a greenfield phase (first code in the repo), not a rename/refactor/migration. No prior runtime state exists to inventory.

## Common Pitfalls

### Pitfall 1: Guessing Strands trace/metrics field names instead of verifying against the installed SDK
**What goes wrong:** The exact attribute path for proving a specialist tool was called (`agent.messages` shape, `result.metrics.tool_metrics` key names) was not directly confirmed against a live 1.54.0 install in this research pass — training data and even official-docs summaries can be stale by a minor version or two on exactly this kind of introspection API.
**Why it happens:** Docs pages for "Agents as Tools" focus on the happy-path wiring code, not on how to assert the wiring worked; the metrics/traces docs page is written from a general observability angle, not "how do I unit-test this."
**How to avoid:** Before writing the final assertion in the smoke test, run it once with `print(supervisor.messages)` and `print(result.metrics.tool_metrics)` uncommented, inspect the real output shape from the installed `strands-agents==1.54.0`, then write the assertion against what's actually observed — not against this document's example code verbatim.
**Warning signs:** `AttributeError` on `result.metrics.tool_metrics`, or `agent.messages` items not having the expected `content`/`role` keys.

### Pitfall 2: Treating BedrockModel construction success as proof of connectivity
**What goes wrong:** `BedrockModel(model_id=..., region_name=...)` never raises on bad credentials or missing model access — it's a plain Python object construction with no network call. A smoke test that only constructs the model and the `Agent` and declares success has verified nothing about Bedrock actually working.
**Why it happens:** It's tempting to treat "no exception during setup" as "the connection works," especially when writing the smoke test quickly.
**How to avoid:** The smoke test must call `agent("...")` with an actual (cheap, short) prompt and only declare success after that call returns.
**Warning signs:** The smoke test "passes" even when run with completely fake/invalid AWS credentials — a immediate red flag it isn't calling Bedrock at all.

### Pitfall 3: Region/credential defaults silently pointing at the wrong place
**What goes wrong:** If `region_name` is left unset, `BedrockModel` falls back through boto3 session → `AWS_REGION` env var → hardcoded `us-west-2` default [CITED: strandsagents.com Amazon Bedrock docs]. This environment has no `AWS_REGION` set (confirmed below) and injected placeholder credentials (`AWS_ACCESS_KEY_ID=proxy-injected`, `AWS_SECRET_ACCESS_KEY=proxy-injected`) — these will authenticate against nothing real and should surface as `UnrecognizedClientException`, not `NoCredentialsError`, since credentials are technically present but invalid.
**Why it happens:** Assuming "no credentials" is the only failure mode; forgetting a sandboxed/CI environment may have fake-but-present credential env vars that pass the "are credentials set" check but fail authentication.
**How to avoid:** The smoke test's exception handling must branch on `ClientError`'s `Error.Code`, not just on "credentials present vs absent" — see Pattern 4 above, which explicitly handles `UnrecognizedClientException` as a distinct, correctly-diagnosed case.
**Warning signs:** A smoke test that only catches `NoCredentialsError` and lets `ClientError` bubble up as a raw traceback in an environment with present-but-invalid credentials — exactly this environment's condition.

## Code Examples

Verified/cited patterns — see full listings under Architecture Patterns 1–4 above:
- Pattern 1: `models/engagement_record.py` — full Pydantic v2 `EngagementRecord` + slice models.
- Pattern 2: `store/engagement_store.py` + `store/file_engagement_store.py` — abstract interface + atomic-write file implementation.
- Pattern 3: `backend/scripts/smoke_test_agents_as_tools.py` — throwaway 2-agent agents-as-tools smoke test with trace assertions.
- Pattern 4: `backend/scripts/smoke_test_bedrock_connectivity.py` — `BedrockModel` wiring with fail-fast, readable exception handling.

### Single-writer enforcement test (REC-03)
```python
# tests/test_single_writer.py
"""Enforces REC-03 / D-05: no module under agents/ or tools/ may import the store."""
import ast
from pathlib import Path

FORBIDDEN_MODULE_PREFIXES = ("store", "backend.store")
SCAN_DIRS = ["agents", "tools"]

def _imported_module_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names

def test_no_agent_or_tool_module_imports_store():
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for dir_name in SCAN_DIRS:
        scan_dir = repo_root / dir_name
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            imported = _imported_module_names(py_file)
            for module in imported:
                if any(module == p or module.startswith(p + ".") for p in FORBIDDEN_MODULE_PREFIXES):
                    violations.append(f"{py_file}: imports '{module}'")
    assert not violations, (
        "REC-03 violation — agent/tool modules must never import the store "
        f"directly:\n" + "\n".join(violations)
    )
```
This passes trivially today (both `agents/` and `tools/` are empty placeholder packages per the Recommended Project Structure) and becomes a real regression guard the moment Phase 2 adds specialist code — exactly the intent of building the boundary now.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Pydantic v1 `.dict()`/`.json()`/`.parse_raw()` | Pydantic v2 `.model_dump()`/`.model_dump_json()`/`.model_validate_json()` | Pydantic 2.0 (2023) | This project's `pydantic>=2.13` install only has the v2 API; using v1-era method names raises `AttributeError` |
| Pre-1.0 Strands (`strandsagents.com/0.1.x/...`) multi-agent examples | Current (post-1.0) `agents-as-tools`/`Graph`/`Swarm` API surface | Strands 1.0 stabilization (per STACK.md, mid-2026) | Pre-1.0 code samples found via general web search commonly use stale import paths (`strands.models.bedrock` vs current) — always confirm against the non-versioned `/docs/...` path or the pinned version's own docs |

**Deprecated/outdated:** None specific to this phase beyond the Pydantic v1→v2 and Strands pre-1.0→1.0 transitions already noted.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | Exact `agent.messages` content-block key names (`toolUse` vs `tool_use`) and `result.metrics.tool_metrics` dict shape, as written in the Pattern 3 code example | Architecture Patterns → Pattern 3 | Low — the example explicitly instructs verifying the real shape via `print()` before finalizing the assertion; the smoke test naturally fails loudly (`AttributeError`/`KeyError`) rather than silently passing on wrong assumptions, so the risk is a short debugging step, not a hidden bug |
| A2 | `pytest` and `python-dotenv` versions are current/compatible without independent registry verification this session | Standard Stack → Supporting | Low — both are extremely stable, widely-used packages; a version conflict would surface immediately as an install error, not a silent failure |
| A3 | `strands-agents`' internal `botocore`/`boto3` version pins are compatible with directly importing `botocore.exceptions` in the smoke test (not independently confirmed via a fresh `pip install` + `pip show` in this research pass) | Architecture Patterns → Pattern 4 | Low — `botocore` is a transitive dependency of `boto3`, which `strands-agents` requires; `botocore.exceptions` is stable, long-standing API surface across versions |

**If this table is empty:** N/A — see entries above; all are LOW risk with fast, self-evident failure modes if wrong.

## Open Questions

1. **Exact current Claude model slug for `BEDROCK_MODEL_ID`'s documented default**
   - What we know: STACK.md and this research consistently recommend an inference-profile-form id (`us.` or `global.` prefixed), e.g. `us.anthropic.claude-sonnet-4-6`, and warn that bare foundation-model ids commonly throw `ValidationException` for on-demand invocation.
   - What's unclear: The exact current slug is account/region-specific (depends on which models are enabled in the team's AWS account's Bedrock "Model access" page) and drifts as AWS renames/versions models — this research cannot confirm the live value for this specific AWS account.
   - Recommendation: Treat the `BEDROCK_MODEL_ID` env var's default as a placeholder to be confirmed against the AWS Bedrock console before the smoke test is expected to pass; the smoke test's job (per D-08) is to fail fast and readably if it's wrong, not to guess the correct value.

2. **Whether this sandbox/executor environment will have real AWS credentials at plan-execution time**
   - What we know: This research environment has `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` set to the literal placeholder string `"proxy-injected"` and no `AWS_REGION` set — these will not authenticate against real AWS Bedrock.
   - What's unclear: Whether the executor agent's environment (which may differ from this research session's sandbox) has real, working AWS credentials.
   - Recommendation: The Bedrock smoke test must be verified to produce a *readable failure* (not a crash) in this exact placeholder-credential condition as part of its own acceptance criteria, since success against real Bedrock cannot be guaranteed to be testable in every execution environment. REC-01/02/03 (the Pydantic model + store + single-writer test) must not depend on this smoke test passing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python | strands-agents (requires ≥3.10), Pydantic, all backend code | ✓ | 3.11.15 | — |
| pip | Package installation | ✓ | 24.0 | — |
| git | Version control / GSD workflow | ✓ | 2.43.0 | — |
| AWS CLI | Optional convenience for `aws configure` local credential setup | ✗ | — | boto3's credential chain also reads plain env vars / `~/.aws/credentials` directly; AWS CLI is not required for the smoke test to run (only for interactive credential setup) |
| Working AWS credentials (real Bedrock access) | Bedrock connectivity smoke test success path (ORC-03) | ✗ | `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` present but literal placeholder value `"proxy-injected"` [VERIFIED: `env \| grep -i AWS` this session] | Per D-08, the smoke test must fail fast with a readable diagnosis in this condition — this is itself a first-class success criterion for the phase, not a blocker. The Pydantic model / store / single-writer deliverables (REC-01/02/03) have zero AWS dependency and must be independently verifiable regardless of this smoke test's outcome. |
| `AWS_REGION` env var | Region resolution fallback for `BedrockModel` if `region_name` omitted | ✗ (unset) [VERIFIED: `env \| grep -i region` this session, no output] | — | D-06 requires explicit `region_name`/`BEDROCK_MODEL_ID`/`AWS_REGION`-sourced construction regardless, so an unset env var is expected to be overridden by an explicit default in code, not silently fall through to boto3's `us-west-2` default |

**Missing dependencies with no fallback:** None — every gap above has a documented fallback or is itself the condition the smoke test is designed to detect and report.

**Missing dependencies with fallback:** AWS CLI (not required, boto3 reads env/config directly); working Bedrock credentials (the smoke test's fail-fast behavior is the fallback, per D-08).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (not yet configured in this greenfield repo — this phase's Wave 0 gap) |
| Config file | none — see Wave 0 gaps below |
| Quick run command | `pytest backend/tests/ -x -q` |
| Full suite command | `pytest backend/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| REC-01 | `EngagementRecord` validates with only `job` populated; rejects invalid `triage.verdict` values | unit | `pytest backend/tests/test_engagement_record.py -x -q` | ❌ Wave 0 |
| REC-02 | `FileEngagementStore.create/get/save` round-trips a record to `data/engagements/{id}.json` and back, including atomic-write behavior | unit | `pytest backend/tests/test_file_engagement_store.py -x -q` | ❌ Wave 0 |
| REC-03 | No module under `agents/`/`tools/` imports `store` (AST-based import-graph check) | unit (static analysis) | `pytest backend/tests/test_single_writer.py -x -q` | ❌ Wave 0 |
| ORC-03 | `smoke_test_agents_as_tools.py` proves an independent specialist tool-call trace; `smoke_test_bedrock_connectivity.py` succeeds or fails fast with a readable message | manual / smoke-script (not `pytest`-automated — these are throwaway scripts per D-08, run directly and their console output inspected) | `python -m backend.scripts.smoke_test_agents_as_tools` / `python -m backend.scripts.smoke_test_bedrock_connectivity` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x -q`
- **Per wave merge:** `pytest backend/tests/ -v` plus a manual run of both smoke-test scripts with their console output captured in the plan's verification evidence
- **Phase gate:** Full suite green before `/gsd-verify-work`; Bedrock smoke test result (pass OR clean fail-fast diagnosis) recorded as evidence either way — a readable failure due to this environment's placeholder credentials is an acceptable phase-gate outcome per D-08's own design intent, a silent crash/traceback is not

### Wave 0 Gaps
- [ ] `backend/tests/__init__.py` + a `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` block (`testpaths = ["backend/tests"]`) — no test framework config exists yet in this greenfield repo
- [ ] `backend/tests/test_engagement_record.py` — covers REC-01
- [ ] `backend/tests/test_file_engagement_store.py` — covers REC-02 (use `tmp_path` pytest fixture to avoid polluting real `data/engagements/`)
- [ ] `backend/tests/test_single_writer.py` — covers REC-03 (code given verbatim above under Code Examples)
- [ ] Framework install: `pip install pytest` — none present yet

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | no | No user-facing auth in this phase (no HTTP endpoints exist yet) |
| V3 Session Management | no | No session concept in this phase |
| V4 Access Control | no | No multi-actor access boundary in this phase's scope (single local process) |
| V5 Input Validation | yes | Pydantic v2 `BaseModel` validation on `EngagementRecord` and all stage slices — reject malformed data at the model boundary rather than downstream |
| V6 Cryptography | no | No cryptographic operations in this phase; AWS credential handling is delegated entirely to boto3's own credential chain (never hand-roll credential storage/parsing) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Path traversal via a maliciously crafted `engagement_id` used to construct a file path (`data/engagements/{id}.json`) | Tampering | `engagement_id` is a server-generated `uuid4` (D-04), never taken as free-form user input for path construction — `FileEngagementStore._path()` must only ever receive a `UUID` object (Pydantic-validated), not a raw string, closing off `../../etc/passwd`-style injection |
| Committing real AWS credentials to the public hackathon repo (via a hardcoded default in the smoke test, or a checked-in `.env`) | Information Disclosure | Never hardcode a real `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` default in `smoke_test_bedrock_connectivity.py`; rely solely on the boto3 credential chain (env vars / `~/.aws/credentials` / instance role), and ensure any `.env` file is gitignored (per PITFALLS.md Security Mistakes table) |
| Torn/partially-written JSON file corrupting the Engagement Record store on process interruption | Tampering (data integrity) | Atomic write via temp-file + `os.replace` (Pattern 2 above), not a direct write to the final path |

## Sources

### Primary (HIGH confidence)
- `.planning/research/STACK.md` — Strands package/version, agents-as-tools code shapes, `BedrockModel` wiring, FastAPI/Pydantic patterns (project-internal, already fetched-and-verified research)
- `.planning/research/ARCHITECTURE.md` — component boundaries, sole-writer pattern, build order (project-internal)
- `.planning/research/PITFALLS.md` — guessed-API risk, Bedrock region/credential traps, single-wrapped-call risk (project-internal)
- `docs/PRD.md` §6.2 — exact Engagement Record JSON shape (project-internal)
- https://pypi.org/project/strands-agents/ — version 1.54.0, 2026-08-27, Python ≥3.10 requirement (fetched directly this session)
- `pip index versions strands-agents` / `pydantic` / `boto3` — live registry version confirmation (run directly this session)

### Secondary (MEDIUM confidence)
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/ — `@tool`-wrapped specialist pattern, `.as_tool()`, bare-list inclusion (fetched directly this session)
- https://strandsagents.com/docs/user-guide/observability-evaluation/metrics/ — `AgentResult.metrics`/`EventLoopMetrics`/`tool_metrics` (fetched directly this session; exact runtime shape not independently confirmed against a live 1.54.0 install — see Assumptions Log A1)
- https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/ — `BedrockModel` constructor args, region resolution order (fetched directly this session)
- https://strandsagents.com/docs/user-guide/quickstart/python/ — minimal `Agent`/`@tool` construction (fetched directly this session)
- botocore exception types (`NoCredentialsError`, `ClientError`, `UnrecognizedClientException`, `AccessDeniedException`, `ValidationException`) — general web search across multiple AWS/community sources (repost.aws, GitHub issues), not a single official docs page fetch; MEDIUM confidence, this is stable/long-standing botocore API surface

### Tertiary (LOW confidence)
- None used as authoritative for any code example in this document — all Strands-specific code shapes trace to a direct docs fetch this session or to the already-verified project-internal STACK.md.

## Metadata

**Confidence breakdown:**
- Standard stack (versions, package legitimacy): HIGH — directly verified via `pip index versions` and PyPI page fetches this session
- Architecture (Pydantic model, store interface, project structure): HIGH — standard, well-established patterns with no SDK-version dependency
- Strands trace-inspection / Bedrock exception surface: MEDIUM — verified against current docs fetches, but exact runtime attribute shapes for `agent.messages`/`result.metrics.tool_metrics` were not confirmed against a live running instance of 1.54.0 in this research pass (flagged explicitly in Pitfall 1 and Assumption A1 for build-time verification)
- Pitfalls: HIGH — directly sourced from project-internal PITFALLS.md, itself researched against live Strands docs

**Research date:** 2026-09-01
**Valid until:** 7 days (Strands SDK is releasing frequently per STACK.md — re-verify exact trace/metrics attribute names against the actually-installed version at implementation time regardless of this document's age)
