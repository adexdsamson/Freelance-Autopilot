# Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring - Research

**Researched:** 2026-09-08
**Domain:** Strands Agents SDK multi-tool supervisor wiring, deterministic dual-use tools, FastAPI stage routing
**Confidence:** HIGH (core mechanics verified directly against installed `strands-agents==1.54.0` source and existing Phase 3/5 code; deterministic rule *design* is discretionary/ASSUMED per CONTEXT.md)

## Summary

Phase 6 is almost entirely a **generalization exercise**, not new-technology research. Phases 3 and 5
already established every mechanical pattern this phase needs: agents-as-tools supervisor construction,
toolResult-based typed extraction, a runner DI seam with a deterministic default + env-selected live
path, dual-use `@tool` functions, and the FastAPI sole-writer merge-and-persist flow. The one genuinely
new mechanic is **multi-tool toolResult disambiguation**: today's `extract_triage_result` /
`extract_proposal_result` scan for the *first* `toolResult` block with a `"json"` entry because each
existing supervisor has exactly one tool. `build_full_supervisor()` registers three tools on one
Supervisor, so a trace can legitimately contain multiple `toolResult` blocks (from a single call, or
across a conversation) and the naive first-match scan would silently pick the wrong specialist's
result if ever more than one appears. I read the installed SDK source directly
(`strands/agent/_agent_as_tool.py`, `strands/event_loop/event_loop.py`, `strands/types/tools.py`) to
confirm the exact two-pass algorithm needed: `ToolUse` blocks (which carry `name` + `toolUseId`) live on
*assistant* messages; `ToolResult` blocks (which carry only `toolUseId`, **no name**) live on the
following *user* message. Disambiguation by name therefore requires first indexing `toolUseId -> name`
from every `toolUse` block in the trace, then filtering `toolResult` blocks against that index before
reading the first matching `json` content block — this is Section "Code Examples" below, and it is a
drop-in generalization that keeps the existing two extractors working unchanged (or lets them be
rewritten to call the same shared, name-parameterized helper).

Everything else — the `OpsRunner` seam, the three ops `@tool` functions, the fixtures, the `/advance`
stage=ops branch, and the typed `OpsSlice` — is a direct structural copy of the Phase 3/5 idioms with
domain-specific bodies. The one design decision requiring genuine judgment (left to Claude's discretion
per CONTEXT.md) is the deterministic scope-creep/overdue rule itself; this research proposes concrete,
conditional rules mirroring `check_scope_clarity`'s keyword-marker pattern, tagged `[ASSUMED]` because
they are original design, not verified against any external source.

**Primary recommendation:** Add `build_full_supervisor()` + a shared `_find_tool_result_json(messages,
tool_name)` two-pass (toolUse-index, then toolResult-filter) helper in `supervisor.py`; add
`backend/agents/ops_agent.py` + `backend/agents/ops_runner.py` + three `backend/tools/check_scope_creep.py`
/ `check_invoice_status.py` / `draft_status_update.py` modules mirroring the Phase 5 tool files exactly;
extend the existing `elif stage == "ops":` seam in `api.py` with a `fixture: str = "creep"` query param,
a 409 contract-precondition guard, and the same try/except/`map_bedrock_error`/503 shape already proven
for `stage=proposal`; tighten `OpsSlice`'s three `list[dict]` fields to typed card models without
renaming them.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Unified 3-tool Supervisor construction | API/Backend (Strands agent layer, in-process with FastAPI) | — | `build_full_supervisor()` is a pure Python object graph built inside the same backend process; no separate service |
| Name-disambiguated toolResult extraction | API/Backend | — | Pure trace-walking logic over `Agent.messages`, no I/O |
| Deterministic ops tools (`check_scope_creep`, `check_invoice_status`, `draft_status_update`) | API/Backend | — | Plain Python functions, `@tool`-decorated for dual reuse; no network, no store |
| Fixture data (client thread, payment schedule, jobs) | API/Backend (bundled static data) | — | Read from `backend/fixtures/*.json` at call time; not a database, not user-editable at runtime |
| `OpsRunner` DI seam (env-selected backend) | API/Backend | — | FastAPI dependency-injection function selecting deterministic vs. live implementation |
| `/advance?stage=ops` routing + persistence | API/Backend | Database/Storage (via `EngagementStore`) | FastAPI is the sole writer (REC-03); store is a thin JSON-file backend |
| `OpsSlice` typed schema | Database/Storage (persisted shape) | API/Backend (Pydantic validation) | Shared Pydantic model used both for HTTP response serialization and on-disk JSON |

## User Constraints

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add a **new** `build_full_supervisor()` that registers **all three** specialist agents —
  `gig_triage_agent`, `proposal_contract_agent`, `ops_agent` — as agents-as-tools on ONE Supervisor, so
  its tools list contains all three and a run shows **four distinct, independently traceable Agent
  invocations** (SC1). Keep the Phase-3/5 stage-scoped `build_supervisor`/`build_proposal_supervisor`
  intact (do not delete them). Because a 3-tool supervisor can emit multiple toolResult blocks, the
  live-path extraction must **disambiguate by tool name** (`toolUse.name` -> the matching specialist's
  `toolResult` json), generalizing the Phase-3/5 first-json-block scan — this is the
  toolUseId<->name disambiguation Phase 5 deferred. — **Reversibility:** costly — this is the "genuine
  multi-agent orchestration visible in code" the judges score; the extraction contract is load-bearing.

- **D-02:** Build the three PRD §7.3 tools as the ONE source of truth for their rules, `@tool`-decorated
  and dual-use (plain Python for the deterministic path + registered on the Ops Agent for the live
  path), mirroring the Phase-3/5 tool pattern; none import the store (single-writer, REC-03):
  - `check_scope_creep` — compares incoming (fixture) client-thread messages against the signed SOW's
    enumerable deliverables and flags creep (OPS-01).
  - `check_invoice_status` — flags milestones overdue against the payment schedule (OPS-02).
  - `draft_status_update` — a client-ready status summary reflecting whatever flags are currently active
    (OPS-03, SC4). A distinct `build_ops_agent()` specialist Agent wraps these for the live path.

- **D-03:** Add an `OpsRunner` DI seam (`get_ops_runner`, `_deterministic_ops_runner`,
  `_supervisor_ops_runner`, `OPS_BACKEND` env) exactly like Phase 3/5. Deterministic is the **default**
  (offline, demo-repeatable); `OPS_BACKEND=supervisor` selects the live path. The runner takes the
  record (its contract SOW) + the loaded fixture thread + payment schedule -> a typed ops result
  (status update + escalation cards). — **Reversibility:** reversible — body change behind a stable
  interface.

- **D-04:** Ship `backend/fixtures/`: `sample_client_thread.json` (a thread containing a **deliberate
  scope-creep message**) plus a **clean variant** (no creep); `sample_payment_schedule.json` (**one
  overdue milestone**) plus a **clean variant** (none overdue); and `sample_upwork_jobs.json` (5–8
  mixed-fit postings). A **variant selector** (e.g. an `/advance` `fixture=creep|clean` param, or a
  loader key) drives SC2 (creep -> 2 cards) vs SC3 (clean -> 0 cards). Fixtures are pure data (no store
  import). — **Reversibility:** reversible.

- **D-05:** Extend the existing `/advance` handler's stage guard with the already-stubbed
  `elif stage == "ops":` branch: load the record, guard the ops precondition (a contract/SOW must
  exist — otherwise a 4xx), run the specialist via the `OpsRunner` DI seam, merge the typed ops result
  **VERBATIM** into the `ops` slice, persist via `store.save()`, return the updated record. Reuse
  `map_bedrock_error` -> credential-free **503**. After this, `/advance` routes+completes **both**
  `proposal` and `ops` (API-03). — **Reversibility:** costly — the endpoint's stage-routing +
  status-code contract is what clients and the demo build on.

- **D-06:** Each scope-creep flag, each invoice flag, and any judgment-needed status is a **distinct
  escalation card** in the ops output (OPS-04). The checks are **conditional**, not hardcoded: the clean
  fixture variant yields **zero** cards (SC3), the creep+overdue variant yields **exactly two** (SC2).
  Represent cards as a typed model so counts are machine-checkable.

- **D-07:** `OpsSlice` currently holds `status_updates`/`scope_creep_flags`/`invoice_flags` as
  `list[dict]`; tighten to typed cards where it makes the SC2/SC3 assertions cleaner. Enriching the
  Phase-1 stub is in scope. — **Reversibility:** costly — persisted record shape.

- **D-08:** Offline tests (no creds) MUST pass and verify: (a) `build_full_supervisor()` constructs
  offline with all three specialist tools registered and four distinct Agent instances (SC1, ORC-01) —
  construction-only, no network; (b) the creep+overdue fixture -> exactly two distinct escalation cards
  (SC2); (c) the clean fixture -> zero cards (SC3); (d) `draft_status_update` reflects the active flags
  (SC4); (e) `/advance` routes+completes **both** `proposal` and `ops` stages, returning the updated
  record each time (SC5); (f) the ops slice is merged FastAPI-only (REC-03); (g) `/advance` ops fails
  fast + readably (503, never a raw 500) when the live path raises. The **live four-agent Bedrock
  trace** (`OPS_BACKEND=supervisor` / the unified supervisor) is documented **manual** verification,
  exactly as in Phases 1/3/5.

### Claude's Discretion

Module layout (`backend/agents/ops_agent.py`, `backend/agents/ops_runner.py`,
`backend/tools/{check_scope_creep,check_invoice_status,draft_status_update}.py` per PRD §12, vs
consolidating), the exact typed card/result model names, the precise ops-precondition 4xx code, the
fixture-variant selector mechanism, the deterministic creep/overdue rules, and whether
`build_full_supervisor` lives in `supervisor.py` — all at Claude's discretion, consistent with the
Phase 3/5 idioms.

### Deferred Ideas (OUT OF SCOPE)

- Chrome MV3 extension (CAP-01..03) — Phase 4.
- Real Gig Triage tools (TRI-01..04) — Phase 2, behind the existing seam.
- Deterministic end-to-end demo run, README, demo script, architecture diagram, OSI license
  (DEMO-02..05) — Phase 7.
- AgentCore Memory/Runtime (DEPLOY-01/02) — Phase 8 (cut-first).

None else — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORC-01 | A Strands Supervisor agent orchestrates three distinct specialist Agent instances via agents-as-tools (four separately traceable agents) | §"Code Examples" Pattern 1 (`build_full_supervisor`), §"Architecture Patterns" Pattern 1; verified against installed `strands-agents==1.54.0` `_AgentAsTool`/`as_tool()` source |
| API-03 | `POST /engagements/{id}/advance` advances to proposal then ops, returns updated record | §"Code Examples" Pattern 4 (`/advance` ops branch); mirrors existing `stage=proposal` branch verbatim |
| OPS-01 | `check_scope_creep` compares fixture client messages vs. signed SOW deliverables, flags creep | §"Code Examples" Pattern 2; §"Common Pitfalls" Pitfall 2 |
| OPS-02 | `check_invoice_status` flags milestones overdue vs. payment schedule | §"Code Examples" Pattern 2; §"Common Pitfalls" Pitfall 1 (date determinism) |
| OPS-03 | `draft_status_update` generates client-ready status summary | §"Code Examples" Pattern 2 |
| OPS-04 | Each scope-creep flag / invoice flag / judgment-needed status is a distinct escalation card | §"Standard Stack" typed-model section; §"Don't Hand-Roll" |
| DEMO-01 | Fixtures seed Stages 2-3 deterministically (jobs, client thread w/ creep, payment schedule w/ overdue milestone) | §"Code Examples" Pattern 3 (fixture loader + variant selector) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Use `strands-agents` (import name `strands`) — version installed and pinned: **1.54.0** (verified via
  `pip3 show strands-agents` this session). Do not follow pre-1.0 docs/examples.
- Supervisor/specialist pattern: **Agents-as-Tools** (`Agent.as_tool()`), never `Graph`/`Swarm` for this
  deterministic, judged demo.
- `@tool`-decorated plain functions; typed dict/Pydantic returns, not hand-built `ToolResult` objects.
- `agent.structured_output()` / `structured_output_model=` is the mechanism for forced typed output —
  already used by `gig_triage_agent.py` and `proposal_contract_agent.py`; `ops_agent.py` must follow
  the same pattern.
- `BedrockModel(model_id=..., region_name=...)` explicit construction — never a bare model-id string
  passed to `Agent(model="...")`.
- FastAPI is the sole Engagement Record writer; agents/tools never mutate the record or import the
  store (enforced by `backend/tests/test_single_writer.py`, an AST-based import scan of
  `backend/agents/` and `backend/tools/`).
- No new external packages are needed for this phase (all of `strands-agents`, `pydantic`, `fastapi`,
  `boto3`, `pytest`, `httpx` are already installed and pinned from Phases 1/3/5) — the Package
  Legitimacy Audit below is a short-circuit confirmation, not a new-install review.

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** All required packages
(`strands-agents==1.54.0`, `pydantic==2.13.5`, `fastapi==0.141.1`, `pytest==9.1.1`, `httpx==0.28.1`,
`boto3`) are already installed and were verified/legitimacy-audited in Phase 1's STACK research. This
phase adds only in-repo modules (`backend/agents/ops_agent.py`, `backend/agents/ops_runner.py`,
`backend/tools/check_scope_creep.py`, `backend/tools/check_invoice_status.py`,
`backend/tools/draft_status_update.py`) and static JSON fixtures under `backend/fixtures/` — no
`pip install` / `npm install` step is required.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none — no new packages this phase)* | — | — | — | — | — | N/A |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `strands-agents` | 1.54.0 (installed, `[VERIFIED: pip3 show strands-agents]`) | `Agent`, `.as_tool()`, `@tool`, `BedrockModel`, `structured_output_model` | Already the project's core framework since Phase 1; no new package needed |
| `pydantic` | 2.13.5 (installed, `[VERIFIED: pip3 show pydantic]`) | Typed `OpsResult`/escalation-card models, `OpsSlice` schema | Same schema layer already used for `TriageSlice`/`ProposalContractResult` |
| `fastapi` | 0.141.1 (installed, `[VERIFIED: pip3 show fastapi]`) | `/advance?stage=ops` route, query params, dependency injection | Already the project's HTTP layer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.1.1 (installed) | Offline test suite for all D-08 assertions | Already the project's test runner |
| `httpx` | 0.28.1 (installed, via `fastapi.testclient.TestClient`) | End-to-end `/advance` stage=ops HTTP tests | Already used in `test_advance_endpoint.py` |
| Python stdlib `datetime`/`date` | 3.11 stdlib | Overdue-date comparison in `check_invoice_status` | No third-party date library needed for simple calendar-date comparison (avoid `dateutil`/`arrow` — unneeded complexity for ISO date strings) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Query param `fixture=creep\|clean` on `/advance` | A separate `/engagements/{id}/fixtures/{variant}` endpoint, or fixture keyed off engagement content | Query param is the minimal-surface-area choice, consistent with the existing `stage=` query param already on `/advance`; a separate endpoint adds API surface for no benefit in a demo-only feature |
| Two-pass toolUseId->name index + toolResult filter | Regex/string scan of the raw message JSON for the tool name | The typed two-pass walk is exactly what the SDK's own message shape supports (`ToolUse.name` / `ToolResult.toolUseId`) and matches the existing extractor's defensive non-dict-tolerant style; string scanning would be fragile and duplicate parsing logic already proven safe |
| Python stdlib `date` comparison for overdue detection | `freezegun` / injected `datetime.now` monkeypatch | Fixture dates chosen as fixed, already-past (or far-future) absolute ISO dates make the check deterministic forever relative to wall-clock `date.today()` — no test-time clock mocking library needed (see Pitfall 1) |

**Installation:** No new installs required — all packages already present. If accidentally removed:
```bash
pip3 install --user strands-agents==1.54.0 pydantic fastapi boto3 pytest httpx
```

**Version verification:** confirmed this session via `pip3 show strands-agents pydantic fastapi pytest httpx` (all present, versions above). No stale training-data assumption was used for version numbers.

## Architecture Patterns

### System Architecture Diagram

```
                        POST /capture                         POST /advance?stage=proposal
                              |                                          |
                              v                                          v
                     +-----------------+                        +-----------------+
                     |   FastAPI app   |<-----------------------+|   FastAPI app   |
                     |  (backend/api)  |   store.get/save        |  (sole writer)  |
                     +--------+--------+                        +--------+--------+
                              |                                          |
                     TriageRunner (DI)                          ProposalRunner (DI)
                              |                                          |
                deterministic |  supervisor                deterministic | supervisor
                (default)     |  (OPS_BACKEND=              (default)    | (PROPOSAL_BACKEND=
                              |   supervisor)                            |  supervisor)
                              v                                          v
                 placeholder_kill_switch_check          check_scope_clarity/draft_proposal/draft_contract
                     (plain function call)                    (plain function calls, in sequence)

  ---------------------------- NEW in Phase 6 ----------------------------------------------------

                                    POST /advance?stage=ops&fixture=creep|clean
                                                     |
                                                     v
                                          +-----------------------+
                                          |     FastAPI app       |
                                          | (guard: contract      |
                                          |  must exist -> 409)   |
                                          +-----------+-----------+
                                                       |
                                              OpsRunner (DI, OPS_BACKEND env)
                                                       |
                              +------------------------+------------------------+
                              |                                                 |
                   deterministic (default)                          supervisor (live, manual-only)
                              |                                                 |
                              v                                                 v
              backend/fixtures/loader.py                        build_full_supervisor()
              load_client_thread(variant)                       tools=[gig_triage_agent,
              load_payment_schedule(variant)                          proposal_contract_agent,
                              |                                        ops_agent]  (4 distinct
                              v                                        Agent instances -- SC1)
          check_scope_creep(thread, contract.text)                            |
          check_invoice_status(schedule, today)                       supervisor("run ops checks...")
          draft_status_update(creep_flags, invoice_flags)                     |
                              |                                   walk supervisor.messages:
                              v                                   1) index toolUse{name,toolUseId}
                    OpsResult (typed, Pydantic)                   2) filter toolResult by
                              |                                      toolUseId in index for
                              v                                      name == "ops_agent"
              api.py merges VERBATIM into record.ops                  3) read first json block
                     (OpsSlice: status_updates,                              |
                      scope_creep_flags, invoice_flags)                      v
                              |                                       OpsResult (typed)
                              v                                              |
                        store.save(record)  <---------------------------------
                              |
                              v
                    return updated EngagementRecord
```

### Recommended Project Structure

```
backend/
├── agents/
│   ├── supervisor.py          # ADD: build_full_supervisor(), shared name-disambiguated
│   │                          #      extraction helper + extract_ops_result(); KEEP
│   │                          #      build_supervisor/build_proposal_supervisor unchanged
│   ├── ops_agent.py           # NEW: build_ops_agent() -- mirrors gig_triage_agent.py /
│   │                          #      proposal_contract_agent.py exactly
│   ├── ops_runner.py          # NEW: OpsRunner Protocol, _deterministic_ops_runner,
│   │                          #      _supervisor_ops_runner, get_ops_runner, OPS_BACKEND
│   ├── triage_runner.py       # unchanged
│   └── proposal_runner.py     # unchanged
├── tools/
│   ├── check_scope_creep.py   # NEW: @tool, dual-use, no store import
│   ├── check_invoice_status.py# NEW: @tool, dual-use, no store import
│   └── draft_status_update.py # NEW: @tool, dual-use, no store import
├── fixtures/
│   ├── __init__.py
│   ├── loader.py               # NEW: pure-data loader, no store import
│   ├── sample_upwork_jobs.json          # NEW: 5-8 mixed-fit postings (DEMO-01)
│   ├── sample_client_thread.json        # NEW: "creep" variant (default) -- deliberate creep message
│   ├── sample_client_thread_clean.json  # NEW: "clean" variant -- no creep
│   ├── sample_payment_schedule.json     # NEW: "creep" variant (default) -- one overdue milestone
│   └── sample_payment_schedule_clean.json # NEW: "clean" variant -- none overdue
├── models/
│   └── engagement_record.py    # MODIFY: OpsSlice fields -> typed card models (D-07)
└── api.py                      # MODIFY: elif stage == "ops": branch (D-05)
```

### Pattern 1: `build_full_supervisor()` — three specialists, one Supervisor

**What:** Register `gig_triage_agent`, `proposal_contract_agent`, and `ops_agent` as three
`.as_tool(..., delegate=True)` tools on a single `Agent`, so `supervisor.tool_names` contains all
three and any live invocation produces four independently traceable `Agent` instances (SC1).

**When to use:** Only for the live path (`OPS_BACKEND=supervisor` / manual-verification trace). The
deterministic default path never constructs or invokes this supervisor.

**Verified against installed source (`strands/agent/agent.py:1090-1134`,
`strands/agent/_agent_as_tool.py`):**
- `Agent.as_tool(*, name=None, description=None, preserve_context=False, delegate=False)` returns an
  `_AgentAsTool` — confirmed present, unchanged signature, in the installed 1.54.0 package.
- Construction (`Agent(...)`, `.as_tool(...)`) performs no network call — `_AgentAsTool.__init__` only
  deep-copies the wrapped agent's initial messages/state; the actual Bedrock call happens inside
  `stream()`, which only runs when the tool is invoked. `[VERIFIED: strands/agent/_agent_as_tool.py:59-113]`
- When the wrapped specialist Agent has `structured_output_model=` set (as `gig_triage_agent.py` and
  `proposal_contract_agent.py` already do, and as `ops_agent.py` must also do), `_AgentAsTool.stream()`
  checks `result.structured_output` **before** the `delegate` branch (`_agent_as_tool.py:256-263`) and
  emits `{"json": result.structured_output.model_dump(mode="json")}` regardless of the `delegate` flag.
  This means the typed-json toolResult path is guaranteed whenever `structured_output_model` is set —
  `delegate=True` only affects what happens if structured output is *absent*.
  `[VERIFIED: strands/agent/_agent_as_tool.py:256-263]`

```python
# Source: backend/agents/supervisor.py pattern, generalized (installed strands-agents==1.54.0
# source read directly: strands/agent/_agent_as_tool.py, strands/agent/agent.py)
def build_full_supervisor() -> Agent:
    """D-01/ORC-01/SC1: registers all three specialists as agents-as-tools on ONE
    Supervisor. Four distinct Agent instances exist after this call: the
    supervisor plus the three specialists it wraps. No network call at
    construction time."""
    gig_triage_agent = build_gig_triage_agent()
    proposal_contract_agent = build_proposal_contract_agent()
    ops_agent = build_ops_agent()

    triage_tool = gig_triage_agent.as_tool(name="gig_triage_agent", delegate=True)
    proposal_tool = proposal_contract_agent.as_tool(name="proposal_contract_agent", delegate=True)
    ops_tool = ops_agent.as_tool(name="ops_agent", delegate=True)

    return Agent(
        system_prompt=(
            "You route each request to exactly ONE specialist tool based on "
            "which stage is being requested: gig_triage_agent for triage, "
            "proposal_contract_agent for proposal/contract drafting, "
            "ops_agent for ops/status-update checks. Never answer yourself, "
            "and never call more than one specialist tool in a single turn."
        ),
        tools=[triage_tool, proposal_tool, ops_tool],
    )
```

### Pattern 2: Dual-use deterministic ops tools

**What:** Three `@tool`-decorated plain functions, each the single source of truth for one PRD §7.3
rule, callable directly (deterministic path) and registered on `ops_agent` (live path).

**When to use:** Always — this is the ONLY place the creep/overdue/status-update logic lives.

```python
# Source: mirrors backend/tools/check_scope_clarity.py's dual-use, keyword-marker pattern
# (backend/tools/check_scope_clarity.py:1-75, read this session)
from __future__ import annotations
from strands import tool

# [ASSUMED] design choice (this research, not verified externally): generic
# scope-creep signal phrases, independent of any specific job's contract text
# -- mirrors check_scope_clarity's keyword-marker approach (TIMELINE_MARKERS/
# DELIVERABLE_MARKERS), which is the ONLY existing precedent for a
# deterministic content-based flag in this codebase.
CREEP_SIGNAL_PHRASES = (
    "can you also", "one more thing", "while you're at it", "can we add",
    "on top of that", "additionally, could you", "also need",
)

@tool
def check_scope_creep(contract_text: str, thread_messages: list[str]) -> dict:
    """Deterministic gate (no LLM): flags client-thread messages containing a
    scope-creep signal phrase not implied by the signed SOW's deliverables.
    Returns {"scope_creep_flags": [{"message": str, "reason": str}, ...]}."""
    flags = []
    for message in thread_messages:
        lowered = message.lower()
        matched = next((p for p in CREEP_SIGNAL_PHRASES if p in lowered), None)
        if matched:
            flags.append({
                "message": message,
                "reason": f"contains scope-creep signal phrase '{matched}' not in the signed SOW",
            })
    return {"scope_creep_flags": flags}
```

```python
# check_invoice_status.py -- OPS-02
from __future__ import annotations
from datetime import date
from strands import tool

@tool
def check_invoice_status(payment_schedule: list[dict], reference_date: str) -> dict:
    """Deterministic gate (no LLM): flags milestones whose due_date is before
    reference_date and are not marked paid. payment_schedule items:
    {"label": str, "amount": float, "due_date": "YYYY-MM-DD", "paid": bool}.
    reference_date: "YYYY-MM-DD" ISO string (explicit, no wall-clock default --
    see Pitfall 1 for why this must not silently default to date.today()).
    Returns {"invoice_flags": [{"milestone_label": str, "due_date": str,
    "days_overdue": int}, ...]}."""
    today = date.fromisoformat(reference_date)
    flags = []
    for item in payment_schedule:
        if item.get("paid"):
            continue
        due = date.fromisoformat(item["due_date"])
        if due < today:
            flags.append({
                "milestone_label": item["label"],
                "due_date": item["due_date"],
                "days_overdue": (today - due).days,
            })
    return {"invoice_flags": flags}
```

```python
# draft_status_update.py -- OPS-03/SC4
from __future__ import annotations
from strands import tool

@tool
def draft_status_update(scope_creep_flags: list[dict], invoice_flags: list[dict]) -> dict:
    """Deterministic template (no LLM): a client-ready status summary that
    reflects whatever flags are currently active. Returns {"text": str}."""
    lines = ["Status update:"]
    if not scope_creep_flags and not invoice_flags:
        lines.append("Engagement is on track -- no scope or invoicing concerns to flag.")
    if scope_creep_flags:
        lines.append(f"{len(scope_creep_flags)} scope item(s) outside the signed SOW were raised in the client thread and need review before proceeding.")
    if invoice_flags:
        lines.append(f"{len(invoice_flags)} milestone(s) are overdue against the payment schedule and need follow-up.")
    return {"text": "\n".join(lines)}
```

### Pattern 3: Fixture variant selector

```python
# backend/fixtures/loader.py -- D-04, pure data, no store import
from __future__ import annotations
import json
from pathlib import Path

_FIXTURES_DIR = Path(__file__).parent

_VARIANT_SUFFIX = {"creep": "", "clean": "_clean"}

def load_client_thread(variant: str = "creep") -> list[str]:
    suffix = _VARIANT_SUFFIX[variant]
    path = _FIXTURES_DIR / f"sample_client_thread{suffix}.json"
    return json.loads(path.read_text())

def load_payment_schedule(variant: str = "creep") -> list[dict]:
    suffix = _VARIANT_SUFFIX[variant]
    path = _FIXTURES_DIR / f"sample_payment_schedule{suffix}.json"
    return json.loads(path.read_text())
```

`/advance?stage=ops&fixture=creep|clean` (default `"creep"`, matching the PRD's base filenames as the
demo default) passes the variant straight through to the loader — no new persisted state, no store
involvement.

### Pattern 4: `/advance` stage=ops branch

```python
# backend/api.py -- extends the existing elif seam (D-05), mirrors the
# stage=proposal branch's guard/merge/persist shape exactly
@app.post("/engagements/{engagement_id}/advance", response_model=EngagementRecord)
def advance(
    engagement_id: UUID,
    stage: str,
    store: Annotated[EngagementStore, Depends(get_store)],
    proposal_runner: Annotated[ProposalRunner, Depends(get_proposal_runner)],
    ops_runner: Annotated[OpsRunner, Depends(get_ops_runner)],
    fixture: str = "creep",
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if stage == "proposal":
        ... # unchanged
    elif stage == "ops":
        if record.contract is None or record.proposal is None or record.proposal.needs_human_input:
            raise HTTPException(
                status_code=409,
                detail="engagement has no signed contract; cannot run ops checks",
            )
        try:
            result: OpsResult = ops_runner(record.contract, fixture)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            mapped = map_bedrock_error(exc)
            raise HTTPException(status_code=503, detail=str(mapped)) from mapped

        record.ops = OpsSlice(
            status_updates=[result.status_update],
            scope_creep_flags=result.scope_creep_flags,
            invoice_flags=result.invoice_flags,
        )
    else:
        raise HTTPException(status_code=400, detail=f"unsupported stage '{stage}'")

    store.save(record)
    return record
```

Note the 409 guard checks `record.proposal.needs_human_input` too — an escalated proposal (no
contract) must not be advanceable to ops; this generalizes the existing 409 guard pattern from
`stage=proposal`'s triage-verdict check.

### Pattern 5: Name-disambiguated multi-tool extraction

```python
# backend/agents/supervisor.py -- generalizes extract_triage_result/
# extract_proposal_result's first-json-block scan for a 3-tool supervisor.
# Verified two-pass algorithm against installed strands-agents==1.54.0:
#   - strands/types/tools.py:65-79 (ToolUse has "name" + "toolUseId", NOT
#     present on ToolResult)
#   - strands/types/tools.py:102-113 (ToolResult has ONLY "toolUseId", no name)
#   - strands/event_loop/event_loop.py:783 (toolUse blocks live on assistant
#     messages: `content["toolUse"]`)
#   - strands/event_loop/event_loop.py:865-866 (toolResult blocks are appended
#     as a "user" role message: {"role": "user", "content": [{"toolResult": r}
#     for r in tool_results]})
def _find_tool_result_json(messages: list[dict], tool_name: str) -> dict:
    """Two-pass walk: (1) index toolUseId -> name from every toolUse block in
    the trace: (2) return the first toolResult json content block whose
    toolUseId maps to `tool_name`. Never reads the Supervisor's own final
    text answer. Tolerates non-dict messages/blocks (mirrors the existing
    extractors' CR-02 defensive style)."""
    tool_use_ids_for_name: set[str] = set()
    for message in messages:
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict):
                continue
            tool_use = block.get("toolUse")
            if isinstance(tool_use, dict) and tool_use.get("name") == tool_name:
                tool_use_id = tool_use.get("toolUseId")
                if isinstance(tool_use_id, str):
                    tool_use_ids_for_name.add(tool_use_id)

    for message in messages:
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            tool_result = block["toolResult"]
            if not isinstance(tool_result, dict):
                continue
            if tool_result.get("toolUseId") not in tool_use_ids_for_name:
                continue
            for content_block in tool_result.get("content", []):
                if isinstance(content_block, dict) and "json" in content_block:
                    return content_block["json"]
    raise RuntimeError(f"{tool_name} tool result not found in supervisor trace")


def extract_ops_result(supervisor_messages: list[dict]) -> OpsResult:
    return OpsResult.model_validate(_find_tool_result_json(supervisor_messages, "ops_agent"))
```

`extract_triage_result`/`extract_proposal_result` can either stay as-is (they are still correct for
their own single-tool supervisors) or be rewritten to call `_find_tool_result_json(messages,
"gig_triage_agent")` / `"proposal_contract_agent"` for consistency — the planner should decide based
on whether touching proven Phase 3/5 code is worth the DRY gain (recommend: leave them untouched, add
the new shared helper alongside, since D-01 explicitly says "keep the Phase-3/5 stage-scoped
build_supervisor/build_proposal_supervisor intact").

### Anti-Patterns to Avoid

- **First-toolResult-wins scan on a multi-tool supervisor:** copying `extract_triage_result`'s exact
  body (scan for the first `toolResult` block with a `"json"` key, no name check) onto
  `build_full_supervisor`'s three-tool trace would silently return whichever specialist's result
  happens to appear first in `supervisor.messages` — correct today only because each existing
  supervisor has one tool. This is exactly the "toolUseId<->name disambiguation Phase 5 deferred"
  D-01 calls out; Pattern 5 above is the fix.
- **Defaulting `check_invoice_status`'s reference date to `datetime.date.today()` inside the tool
  itself:** see Pitfall 1 — always pass an explicit reference date from the caller.
- **Reusing `ContractSlice.payment_schedule` (symbolic `due_marker`, no calendar date) as the ops
  invoice-check input:** it was deliberately designed with a freeform marker instead of a real date
  because no signing date exists at proposal-draft time (see `engagement_record.py:40-41`,
  `[VERIFIED: backend/models/engagement_record.py:37-41]`, quote: `due_marker: str  # freeform symbolic
  marker, e.g. "on_signing" / "on_delivery" / "net_15" — NOT a calendar date (no signing date exists
  yet at draft time).`). The ops-stage fixture payment schedule is a **separate, ops-domain** dataset
  with real `due_date` fields — do not conflate the two schemas.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-tool trace disambiguation | A regex/string search over the raw supervisor message JSON for tool names | The typed two-pass `toolUse`-index / `toolResult`-filter walk (Pattern 5) | The SDK's own `ToolUse`/`ToolResult` TypedDicts already carry exactly the fields needed (`name`+`toolUseId` on one, `toolUseId` alone on the other); string-searching risks false matches inside unrelated text/json blocks |
| Overdue-date determinism | A frozen-clock/monkeypatch library (`freezegun`) | Fixed, already-past absolute ISO dates baked into the fixture + an explicit `reference_date` parameter (no default) on `check_invoice_status` | Simpler, zero new dependency, and stays deterministic forever without needing test-time clock mocking (see Pitfall 1) |
| Escalation-card counting for SC2/SC3 | Ad-hoc dict-shape assertions in tests (`len(result["flags"])`) | Typed Pydantic list fields (`OpsResult.scope_creep_flags: list[ScopeCreepFlag]`) | Matches the project's existing `ProposalContractResult` precedent; makes `len(record.ops.scope_creep_flags) + len(record.ops.invoice_flags) == 2` a one-line, schema-guaranteed assertion |

**Key insight:** every "don't hand-roll" item here is really "don't diverge from the pattern Phase 3/5
already validated" — this phase's entire risk surface is the multi-tool disambiguation generalization,
not new library usage.

## Common Pitfalls

### Pitfall 1: Wall-clock-dependent overdue detection breaks demo determinism

**What goes wrong:** `check_invoice_status` calls `datetime.date.today()` internally as a default, so
SC2's "one overdue milestone" assertion passes only on days after the fixture's due date and SC3's
"zero overdue" assertion could spuriously flip if a clean-variant milestone's due date is not far
enough in the future.

**Why it happens:** Treating "overdue" as an implicit function of wall-clock time rather than an
explicit input makes the demo (and the automated test suite) time-dependent — exactly the kind of
non-determinism DEMO-01 and D-06 are designed to eliminate.

**How to avoid:** (1) Give `check_invoice_status` a **required** `reference_date` parameter with no
default — every caller (the deterministic runner in production, and every test) must supply it
explicitly. (2) Choose fixture due dates that are absolute, already-past calendar dates for the "creep"
variant's overdue milestone (e.g., a date safely in 2025) and absolute, far-future dates for the
"clean" variant (e.g., 2099) — these relationships never change relative to `date.today()` as time
moves forward, so the demo stays deterministic indefinitely without a frozen-clock dependency. (3) The
production `OpsRunner`/`/advance` call site passes `date.today().isoformat()` as `reference_date`; tests
pass a fixed literal string.

**Warning signs:** A test that passes today but is dated to fail at a specific future date; any
`datetime.now()`/`date.today()` call inside `check_invoice_status` itself rather than at the call site.

### Pitfall 2: Conflating the proposal-stage payment schedule with the ops-stage one

**What goes wrong:** Passing `record.contract.payment_schedule` (which has `due_marker: str`, a
symbolic label, never a calendar date — `[VERIFIED: backend/models/engagement_record.py:37-41]`, quote:
`due_marker: str  # freeform symbolic marker, e.g. "on_signing" / "on_delivery" / "net_15" — NOT a
calendar date (no signing date exists yet at draft time).`) directly into `check_invoice_status`, which
expects a real `due_date`, either crashes on a missing key or silently produces zero flags regardless of
the fixture.

**Why it happens:** Both objects are called "payment schedule" and share a superficially similar shape
(label + amount), inviting reuse.

**How to avoid:** Keep them as two distinct schemas: `PaymentMilestone` (proposal-drafting time,
`due_marker`) stays exactly as-is in `engagement_record.py`; the ops-stage fixture
(`sample_payment_schedule.json`) is a separate, ops-domain JSON shape (`label`, `amount`, `due_date`,
`paid`) loaded via `backend/fixtures/loader.py`, never merged into or read from `ContractSlice`.

**Warning signs:** A `KeyError: 'due_date'` when running `check_invoice_status` against
`record.contract.payment_schedule`; SC2's overdue-milestone count silently returning 0.

### Pitfall 3: Skipping the ops-precondition guard lets a headless engagement reach ops

**What goes wrong:** `/advance?stage=ops` runs against an engagement that never had a successful
`stage=proposal` call (or one that escalated with `needs_human_input=True` and no contract) — there is
no signed SOW for `check_scope_creep` to compare against, and the response/persisted record ends up in
an inconsistent state.

**Why it happens:** The existing `stage=proposal` 409 guard checks `record.triage`; a parallel guard is
needed for `stage=ops` checking `record.contract`/`record.proposal`, and it's easy to forget since the
existing branch structure (`if stage != "proposal": raise 400`) has to become a real `elif` chain.

**How to avoid:** Explicit precondition check before invoking `OpsRunner`: `record.contract is None or
record.proposal is None or record.proposal.needs_human_input` -> 409 (mirrors the existing
`record.triage is None or record.triage.verdict != "apply"` -> 409 pattern in the `stage=proposal`
branch, `[VERIFIED: backend/api.py:169-173]`, quote: `if record.triage is None or record.triage.verdict
!= "apply": raise HTTPException(status_code=409, detail="engagement is not apply-triaged; cannot draft
a proposal",)`).

**Warning signs:** A test that calls `/advance?stage=ops` immediately after `/capture` (skipping
`stage=proposal` entirely) and expects anything other than a 409.

### Pitfall 4: Registering `ops_agent` without `structured_output_model` breaks the live extraction path

**What goes wrong:** If `build_ops_agent()` omits `structured_output_model=OpsResult` (unlike
`gig_triage_agent.py`/`proposal_contract_agent.py`, which both set it), the live path's
`_AgentAsTool.stream()` falls through to the `delegate` branch instead of the guaranteed
`result.structured_output` branch (`[VERIFIED: strands/agent/_agent_as_tool.py:256-263]`, code:
`if result.structured_output: yield ToolResultEvent({... "content": [{"json":
result.structured_output.model_dump(mode="json")}]}) elif self._delegate: ...`), which copies raw
text/json content blocks from the specialist's own final message — a much less reliable channel that
depends on the model happening to emit a `json` block in its final answer.

**How to avoid:** `ops_agent.py` must set `structured_output_model=OpsResult` at construction, exactly
like the two existing specialists.

**Warning signs:** The live-path manual verification trace shows a `toolResult` with a `text` block
instead of a `json` block for the `ops_agent` tool.

## Runtime State Inventory

Not applicable — this phase adds new modules and fixtures; it does not rename, refactor, or migrate any
existing runtime state, stored data, or external service configuration. `OpsSlice`'s field-type change
(`list[dict]` -> typed models, D-07) is a **schema tightening**, not a rename: field names
(`status_updates`/`scope_creep_flags`/`invoice_flags`) are unchanged, and no persisted records exist yet
in this project (pre-demo, no production data) — confirmed by inspecting `data/engagements/` is
test-`tmp_path`-scoped only (`backend/tests/conftest.py`, `[VERIFIED: backend/tests/conftest.py:10-15]`,
quote: `"""A FileEngagementStore bound to pytest's tmp_path so tests never touch the real
data/engagements/ directory."""`), so there is no existing on-disk record whose `ops` field would fail
to parse under the new typed schema.

## Code Examples

See Pattern 1-5 under "Architecture Patterns" above — all five are the load-bearing code examples for
this phase (supervisor construction, the three deterministic tools, the fixture loader, the `/advance`
branch, and the name-disambiguated extractor).

### Typed models to add to `backend/models/engagement_record.py`

```python
# D-06/D-07: escalation cards + the Ops specialist's ONE strict typed result,
# mirroring ProposalContractResult's role as the live/deterministic shared contract.
class ScopeCreepFlag(BaseModel):
    message: str
    reason: str

class InvoiceFlag(BaseModel):
    milestone_label: str
    due_date: str
    days_overdue: int

class StatusUpdate(BaseModel):
    text: str

class OpsResult(BaseModel):
    status_update: StatusUpdate
    scope_creep_flags: list[ScopeCreepFlag] = Field(default_factory=list)
    invoice_flags: list[InvoiceFlag] = Field(default_factory=list)

class OpsSlice(BaseModel):
    status_updates: list[StatusUpdate] = Field(default_factory=list)
    scope_creep_flags: list[ScopeCreepFlag] = Field(default_factory=list)
    invoice_flags: list[InvoiceFlag] = Field(default_factory=list)
```

Total escalation-card count for SC2/SC3 assertions: `len(record.ops.scope_creep_flags) +
len(record.ops.invoice_flags)` (status updates are informational, not escalation cards per OPS-04's
wording — "each scope-creep flag, each invoice flag, and any judgment-needed status" — a
judgment-needed status would be a third card type only if the ops tools ever produce one; the current
deterministic design does not, so SC2's "exactly two" = 1 creep + 1 invoice flag).

## State of the Art

Not applicable in the conventional sense (no library API has changed between Phase 5 and Phase 6) —
the installed `strands-agents==1.54.0` version is identical to what Phase 5 verified against
(`[VERIFIED: pip3 show strands-agents]`, confirmed this session). No deprecated/outdated pattern to flag.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The specific `CREEP_SIGNAL_PHRASES` keyword list and `check_scope_creep` rule design | Architecture Patterns Pattern 2 | If the phrases don't match whatever fixture message text gets authored, SC2's "exactly one creep flag" could fail; the planner/executor must co-design the fixture text and the phrase list together (same dependency `check_scope_clarity`'s `TIMELINE_MARKERS` had on job descriptions) |
| A2 | `check_invoice_status`'s exact payment-schedule item shape (`label`/`amount`/`due_date`/`paid`) | Architecture Patterns Pattern 2, Common Pitfalls Pitfall 2 | If the executor picks different field names, the fixture JSON and the tool signature must still agree; low risk since both are authored together in this phase |
| A3 | 409 as the ops-precondition status code | Architecture Patterns Pattern 4 | CONTEXT.md leaves the exact code to discretion; 409 was chosen for consistency with the existing `stage=proposal` guard, but a planner could reasonably pick 422 instead — low risk, purely a status-code choice with no functional impact |
| A4 | Fixture-variant file-naming scheme (`_clean` suffix siblings) | Architecture Patterns Recommended Project Structure, Pattern 3 | CONTEXT.md explicitly defers the exact selector mechanism to discretion; an alternative single-JSON-with-both-variants-keyed design is equally valid and was not chosen here only for simplicity |
| A5 | `OpsResult`/`ScopeCreepFlag`/`InvoiceFlag`/`StatusUpdate` exact model/field names | Code Examples | CONTEXT.md defers "exact typed card/result model names" to discretion; these are a reasonable, precedent-consistent proposal, not a locked requirement |

**If this table is empty:** N/A — see entries above. All five assumptions are explicitly within
CONTEXT.md's "Claude's Discretion" scope, not compliance/security/retention-type claims requiring
separate user sign-off.

## Open Questions

1. **Should `extract_triage_result`/`extract_proposal_result` be refactored to call the new shared
   `_find_tool_result_json` helper, or left untouched?**
   - What we know: D-01 says "keep the Phase-3/5 stage-scoped build_supervisor/build_proposal_supervisor
     intact (do not delete them)" — this is about the *supervisor builders*, not explicitly about the
     extractor functions' internals.
   - What's unclear: whether "intact" extends to forbidding a DRY refactor of the extraction helper
     bodies (which would not change their external behavior/tests, only their implementation).
   - Recommendation: leave `extract_triage_result`/`extract_proposal_result` untouched (safest reading
     of D-01, zero risk to passing Phase 3/5 tests) and add `extract_ops_result` calling the new shared
     helper. This is what Pattern 5 above assumes.

2. **Does the live-path `_supervisor_ops_runner` need the actual signed contract text passed into the
   supervisor prompt, or just a reference to "the current engagement's ops checks"?**
   - What we know: the deterministic path's `OpsRunner.__call__` signature takes `(contract:
     ContractSlice, fixture: str)` per this research's Pattern 4/§"Standard Stack".
   - What's unclear: the exact natural-language prompt string for the live path (mirrors
     `_supervisor_triage_runner`/`_supervisor_proposal_runner`'s `f"... {job.model_dump_json()}"`
     pattern, but `record.contract` + the loaded fixture data together may be a large prompt).
   - Recommendation: mirror the existing pattern exactly — `supervisor(f"Run ops checks for this
     signed contract and fixture data: {contract.model_dump_json()}, fixture={fixture}")` — and let
     `ops_agent`'s own tools (`check_scope_creep`/`check_invoice_status`) load the fixture data
     themselves via `backend/fixtures/loader.py` rather than inlining fixture content into the prompt
     (keeps the prompt small and matches how `gig_triage_agent`/`proposal_contract_agent` delegate all
     actual data-shape work to their tools).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Entire backend | ✓ `[VERIFIED: pip3 show output confirms python3.11 site-packages path]` | 3.11 | — |
| `strands-agents` | ORC-01, `ops_agent.py`, `build_full_supervisor` | ✓ | 1.54.0 | — |
| `pydantic` | `OpsResult`/`OpsSlice`/escalation cards | ✓ | 2.13.5 | — |
| `fastapi` | `/advance?stage=ops` | ✓ | 0.141.1 | — |
| `pytest` + `httpx` | D-08 offline test suite | ✓ | 9.1.1 / 0.28.1 | — |
| AWS Bedrock credentials | `OPS_BACKEND=supervisor` live path | ✗ (sandbox has placeholder AWS creds, per D-08/STATE.md) | — | Deterministic path is the default and fully offline; live four-agent trace is manual-verification-only, exactly as documented in Phases 1/3/5 |

**Missing dependencies with no fallback:** none — the one missing dependency (live Bedrock credentials)
has an explicit, already-established fallback (deterministic default + manual verification).

**Missing dependencies with fallback:**
- AWS Bedrock credentials — deterministic `OpsRunner` path covers all automated tests; live path is
  manual-only per D-08.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (installed, `[VERIFIED: pip3 show pytest]`) |
| Config file | none detected in repo root beyond pytest's default discovery — mirrors Phase 3/5 (no `pytest.ini`/`pyproject.toml` `[tool.pytest]` section found) |
| Quick run command | `cd backend && python -m pytest tests/test_ops_runner.py tests/test_full_supervisor_wiring.py -x` |
| Full suite command | `cd backend && python -m pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORC-01 | `build_full_supervisor()` registers all three specialist tools; four distinct Agent instances exist | unit (construction-only) | `pytest tests/test_full_supervisor_wiring.py -x` | ❌ Wave 0 |
| ORC-01/SC1 | Live 4-agent trace shows four independently traceable invocations | manual-only (needs Bedrock creds) | N/A — documented manual verification | N/A |
| OPS-01 | `check_scope_creep` flags the deliberate creep message, none on clean variant | unit | `pytest tests/test_ops_tools.py::test_check_scope_creep_flags_creep_fixture -x` | ❌ Wave 0 |
| OPS-02 | `check_invoice_status` flags the overdue milestone, none on clean variant | unit | `pytest tests/test_ops_tools.py::test_check_invoice_status_flags_overdue -x` | ❌ Wave 0 |
| OPS-03/SC4 | `draft_status_update` text reflects active flags | unit | `pytest tests/test_ops_tools.py::test_draft_status_update_reflects_flags -x` | ❌ Wave 0 |
| OPS-04/SC2 | creep+overdue fixture -> exactly two distinct escalation cards | integration | `pytest tests/test_ops_runner.py::test_deterministic_ops_runner_creep_fixture_yields_two_flags -x` | ❌ Wave 0 |
| OPS-04/SC3 | clean fixture -> zero escalation cards | integration | `pytest tests/test_ops_runner.py::test_deterministic_ops_runner_clean_fixture_yields_zero_flags -x` | ❌ Wave 0 |
| API-03/SC5 | `/advance` routes+completes both `proposal` and `ops` stages | e2e (TestClient) | `pytest tests/test_advance_endpoint.py::test_advance_ops_after_proposal_completes_both_stages -x` | ❌ Wave 0 |
| API-03 | ops precondition (no contract) -> 409 | e2e (TestClient) | `pytest tests/test_advance_endpoint.py::test_advance_ops_without_contract_returns_409 -x` | ❌ Wave 0 |
| REC-03 | ops agents/tools never import the store | static (AST scan) | `pytest tests/test_single_writer.py -x` (existing test, extended coverage automatically since it scans all of `backend/agents/`+`backend/tools/`) | ✅ (extends existing file) |
| D-08(g) | `/advance` ops fails fast + readably (503) on live-path exception | e2e (TestClient) | `pytest tests/test_advance_bedrock_failfast.py -k ops -x` | ❌ Wave 0 (extend existing file) |
| DEMO-01 | Fixtures present, loadable, variant selector produces the two documented fixture states | unit | `pytest tests/test_fixtures_loader.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_ops_tools.py tests/test_ops_runner.py -x`
- **Per wave merge:** `cd backend && python -m pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_full_supervisor_wiring.py` — covers ORC-01 construction assertions
- [ ] `tests/test_ops_tools.py` — covers OPS-01/02/03
- [ ] `tests/test_ops_runner.py` — covers D-03, SC2, SC3
- [ ] `tests/test_fixtures_loader.py` — covers DEMO-01 loader behavior
- [ ] Extend `tests/test_advance_endpoint.py` — covers API-03/SC5, the 409 ops-precondition guard
- [ ] Extend `tests/test_advance_bedrock_failfast.py` — covers D-08(g) for the ops branch
- [ ] No new framework install needed — pytest already configured and passing per Phase 1/3/5 precedent

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | Out of scope for this demo (single local API key, per PROJECT.md/CLAUDE.md constraints; unchanged by this phase) |
| V3 Session Management | no | No session state introduced by this phase |
| V4 Access Control | no | No new access-control surface; `/advance` remains unauthenticated per existing project scope |
| V5 Input Validation | yes | Pydantic models (`OpsResult`, `ScopeCreepFlag`, `InvoiceFlag`, `StatusUpdate`) validate all specialist output before merge, exactly like `ProposalContractResult`/`TriageSlice`; `fixture` query param should be validated against an explicit `Literal["creep", "clean"]` allow-list (not an arbitrary string used directly in a file path) to avoid an unintended path-traversal vector when building the fixture filename |
| V6 Cryptography | no | No new cryptographic operation introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Path traversal via the new `fixture` query param (e.g. `fixture=../../etc/passwd`) | Tampering | Validate `fixture` against a closed `Literal["creep", "clean"]` set (FastAPI/Pydantic will 422 on any other value) rather than interpolating the raw string into a filesystem path — mirrors the existing `engagement_id: UUID`-typed path param's structural closure of path traversal (`[VERIFIED: backend/api.py:9-11]`, quote: `` `engagement_id` is typed UUID at the path param, which closes path traversal structurally (T-03-03) `` ) |
| Credential/secret leakage in the ops-stage 503 error path | Information Disclosure | Reuse `map_bedrock_error` verbatim (already proven credential-free per Phase 3/5 tests `test_advance_bedrock_failfast.py`) — do not write a parallel/divergent error mapper for the ops branch |
| Store-bypass mutation of the Engagement Record from an ops tool | Tampering | `backend/tests/test_single_writer.py`'s AST scan already covers any new file placed under `backend/agents/` or `backend/tools/` automatically — no test change needed, just adherence to the "never import store" rule in the new modules |

## Sources

### Primary (HIGH confidence)
- `/root/.local/lib/python3.11/site-packages/strands/agent/_agent_as_tool.py` (installed
  `strands-agents==1.54.0`) — read directly this session; `.as_tool()`/`_AgentAsTool.stream()` behavior,
  `structured_output` vs. `delegate` precedence, no-network-at-construction confirmation
- `/root/.local/lib/python3.11/site-packages/strands/agent/agent.py:1090-1134` — `Agent.as_tool()`
  signature, read directly this session
- `/root/.local/lib/python3.11/site-packages/strands/types/tools.py:65-113` — `ToolUse`/`ToolResult`
  TypedDict field definitions (confirms `name` present on `ToolUse` only, absent from `ToolResult`),
  read directly this session
- `/root/.local/lib/python3.11/site-packages/strands/event_loop/event_loop.py:783,865-866` — confirms
  `toolUse` blocks on assistant messages, `toolResult` blocks appended as a "user" role message, read
  directly this session
- `backend/agents/supervisor.py`, `backend/agents/triage_runner.py`, `backend/agents/proposal_runner.py`,
  `backend/agents/gig_triage_agent.py`, `backend/agents/proposal_contract_agent.py`, `backend/api.py`,
  `backend/models/engagement_record.py`, `backend/tools/*.py`, `backend/tests/test_single_writer.py`,
  `backend/tests/conftest.py` — all read directly this session (Phase 3/5 existing code, the canonical
  precedent this phase generalizes)
- `pip3 show strands-agents pydantic fastapi pytest httpx` — versions verified directly this session

### Secondary (MEDIUM confidence)
- `docs/PRD.md` §6.1, §6.2, §7.3, §10, §12 — Ops Agent tool names/output shape, fixture file names,
  repo structure, read directly this session

### Tertiary (LOW confidence)
- None — all claims in this research trace to either directly-read source code/docs this session, or
  are explicitly tagged `[ASSUMED]` in the Assumptions Log as original design proposals within
  CONTEXT.md's stated discretion.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all versions verified this session
- Architecture (supervisor/extraction mechanics): HIGH — verified directly against installed SDK source
- Architecture (deterministic rule design): LOW/discretionary — original proposal, tagged `[ASSUMED]`,
  matches CONTEXT.md's explicit "Claude's Discretion" scope
- Pitfalls: HIGH — each pitfall traces to a specific verified source-code fact (SDK behavior or existing
  project file content)

**Research date:** 2026-09-08
**Valid until:** 30 days (stable — no fast-moving dependency in this phase; re-verify
`strands-agents` version if a `pip3 show` at plan/execute time reports a different version than 1.54.0)
