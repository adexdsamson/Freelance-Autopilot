# Phase 3: Supervisor Wiring + `/capture` Endpoint - Research

**Researched:** 2026-09-02
**Domain:** Strands Agents SDK agents-as-tools orchestration (typed pass-through) + FastAPI/Pydantic API layer + Bedrock fail-fast error handling
**Confidence:** HIGH on the Strands typed-channel mechanics (read directly from the installed `strands-agents==1.54.0` source in this sandbox) and on the Engagement Record/store contract (read directly from Phase 1's code) — MEDIUM on FastAPI/pytest idioms (stable, well-established API surface, WebSearch-verified) — LOW/flagged-ASSUMED on anything requiring a live Bedrock call (this sandbox has placeholder AWS credentials only)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Agents-as-tools wiring (ORC-02)**
- **D-01:** Build the Supervisor with the verified agents-as-tools shape from STACK.md §2 — a specialist `Agent` wrapped in an `@tool`-decorated function, passed into the Supervisor's `tools=[...]`. Two distinct `Agent` instances (Supervisor + Gig Triage specialist) so a trace shows two invocations (success criterion 4). — **Reversibility:** costly — this is the core "genuine multi-agent orchestration" the judging rewards; changing it later touches every specialist.
- **D-02:** The Gig Triage specialist returns a strict typed `TriageResult` (verdict/score/reasoning/extracted_fields — the Engagement Record's triage slice shape). FastAPI merges that typed object into the record **verbatim**; the Supervisor's model must not re-author it (success criterion 3). Enforce by having the triage tool return structured data that FastAPI reads from the tool result / a typed channel, not by parsing the Supervisor's prose.

**Placeholder triage seam (Phase 2 gap)**
- **D-03:** Define the triage seam as a single callable/tool with a fixed signature (raw job fields in → `TriageResult` out). Phase 3 ships a **deterministic placeholder** implementation (e.g. a rule-of-thumb stub: budget-floor + keyword check producing a verdict/score/reasoning) so `/capture` is exercisable and deterministic without Bedrock. Phase 2 replaces the placeholder body with the real `extract_job_fields`/`kill_switch_check`/`llm_scorecard` behind the same signature. — **Reversibility:** reversible — swapping the placeholder for the real agent is a body change behind a stable interface.
- **D-04:** Mark the placeholder clearly in code (name/docstring) as a Phase-2 stand-in so it is not mistaken for the real triage.

**FastAPI as sole writer (REC-03 upheld)**
- **D-05:** `POST /capture` is the only path that creates + saves the record: it constructs the record, runs triage via the Supervisor, merges the typed `TriageResult` into the triage slice, saves through the `EngagementStore`, and returns the verdict. `GET /engagements/{id}` reads via the store and returns 404 for unknown ids. The store is dependency-injected (constructed once, per Phase 1's swap seam).

**Credential-less test strategy (sandbox has placeholder AWS creds)**
- **D-06:** A genuine Supervisor routes to the triage tool via the LLM, which needs Bedrock at runtime. Offline tests (no creds) MUST still pass, so they verify: (a) the FastAPI app + Supervisor construct without error; (b) the `/capture` handler's record-creation + typed-merge + persist + verdict-return path works when the triage seam yields a `TriageResult` (drive it deterministically / inject the placeholder result — no live LLM); (c) `GET /engagements/{id}` round-trips; (d) the Supervisor has the triage specialist registered as a tool. The **live end-to-end orchestration through real Bedrock** (and the two-invocation trace, criterion 4) is a documented **manual** verification, exactly as in Phase 1. `/capture` must fail fast + readably (not 500 with a raw traceback) when Bedrock is unavailable.

### Claude's Discretion
- FastAPI app layout (`backend/api.py` vs an `app/` package), Pydantic request/response models, how the deterministic placeholder is toggled vs the live Supervisor path (e.g. env flag), test client wiring (httpx/TestClient). Choose idioms consistent with STACK.md §5.

### Deferred Ideas (OUT OF SCOPE)
- Real triage tools (`extract_job_fields`, `kill_switch_check`, `llm_scorecard`) — Phase 2 (Engineer B), behind the seam defined here.
- `/engagements/{id}/advance` (proposal/ops) — Phase 5/6.

None else — stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORC-02 | Each specialist returns strict typed JSON that FastAPI merges into the Engagement Record without the Supervisor re-authoring it. | §"Typed-Channel Merge (ORC-02)" below documents the exact, source-verified `strands-agents==1.54.0` mechanism (`structured_output_model` + `.as_tool()`'s ToolResult content, optionally `delegate=True`) that makes the Supervisor's own final-answer text irrelevant to the merge. |
| API-01 | `POST /capture` accepts a structured job payload, runs triage via the Supervisor, writes the result to a new Engagement Record, and returns the verdict. | §"FastAPI Endpoint Design" gives the request/response models (reusing `JobSlice`/`TriageSlice` verbatim from `models/engagement_record.py`), the DI-based triage-runner seam (satisfies D-03/D-06), and the Bedrock fail-fast → 503 mapping. |
| API-02 | `GET /engagements/{id}` returns the current Engagement Record. | §"FastAPI Endpoint Design" — path param typed `UUID` (matches `EngagementStore.get(engagement_id: UUID)` exactly), 404 via `HTTPException`. |
</phase_requirements>

## Summary

Phase 3's hardest technical question — how does FastAPI get the Gig Triage specialist's typed verdict **without** the Supervisor's own LLM re-authoring it? — has a precise, source-verified answer in the installed `strands-agents==1.54.0` package (not just docs): the `@tool`/`.as_tool()` adapter (`strands/agent/_agent_as_tool.py`) checks `result.structured_output` **before** anything else and, when it is set, emits the ToolResult as a raw `{"json": ...}` content block — the specialist's Pydantic-validated dict, untouched. FastAPI can read that content block directly out of `supervisor.messages` (the tool-result trace), completely bypassing whatever prose the Supervisor's final answer contains. This is the "typed channel" D-02 asks for, and it requires no fragile prompt-engineering ("please repeat the JSON verbatim") to work.

A second, source-verified finding resolves an open question from STACK.md/ARCHITECTURE.md: `delegate=True` (which makes the orchestrator's own final answer *become* the specialist's output, skipping an extra LLM round-trip) is explicitly documented as incompatible with "stateful models that manage conversation state server-side" — but the installed `Model` base class defaults `stateful` to `False`, and `BedrockModel` does not override it. So `delegate=True` **is** compatible with this project's Bedrock model provider. Recommendation: use both mechanisms together (`structured_output_model` on the specialist + `delegate=True` on the wrapping `.as_tool()`) for the live path, but do not make the merge *depend* on `delegate` — read the tool-result content block directly, which works whether or not delegation fires.

Because Phase 2 does not exist yet, the actual triage logic behind this wiring must be a **deterministic, non-LLM placeholder** (budget floor + keyword check) — but D-01 still requires two real `Agent` instances to exist in code (construction-only offline; a human runs the live two-invocation trace against real Bedrock, exactly as Phase 1 did for its `echo_specialist` smoke test). The cleanest way to satisfy both constraints without duplicating logic is a single `@tool`-decorated pure-Python function that is (a) registered on the specialist `Agent`'s tool list for the live/demo path, and (b) called **directly as a plain Python function** (the `@tool` decorator preserves normal callability) by a dependency-injected `TriageRunner` seam for the default/offline/test path — one source of truth, two invocation routes, selected by an env flag FastAPI reads once via `Depends`.

**Primary recommendation:** Build `backend/tools/placeholder_triage.py` (one `@tool`-decorated deterministic function, callable directly or via the Agent loop), `backend/agents/gig_triage_agent.py` + `backend/agents/supervisor.py` (real `Agent` objects, construction-only tested offline), and `backend/triage_runner.py` (the DI seam FastAPI injects) — then `backend/api.py` merges whatever `TriageRunner` returns into `record.triage` (reusing `TriageSlice` directly as the typed contract, no new Pydantic model needed) and persists via the existing `EngagementStore`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Job payload validation (`POST /capture` request body) | API / Backend | — | Pydantic model at the FastAPI boundary; no browser/CDN tier involved in this backend-only phase |
| Supervisor→specialist orchestration (agents-as-tools routing) | API / Backend | External Service (Bedrock, live path only) | In-process Strands `Agent` objects live inside the FastAPI process (per ARCHITECTURE.md's "FastAPI ↔ Supervisor: direct in-process Python call") — the network hop only happens if/when the live path invokes Bedrock |
| Typed-result extraction (anti-re-authoring merge) | API / Backend | — | Reads `supervisor.messages`' tool-result content block directly; a pure Python/Pydantic operation, no additional tier |
| Deterministic placeholder triage logic | API / Backend | — | Pure Python (budget floor + keyword check); explicitly NOT an LLM/API-external call per D-03 |
| Engagement Record persistence | Database / Storage | API / Backend (sole writer) | `FileEngagementStore` is the storage tier; FastAPI is the only caller per REC-03/D-05 |
| Engagement retrieval (`GET /engagements/{id}`) | API / Backend | Database / Storage | Read-through: FastAPI validates the path param, store does the lookup |
| Bedrock failure → readable HTTP error | API / Backend | External Service (Bedrock) | The failure boundary is at the API layer's exception handling, even though the fault originates externally |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `strands-agents` | `==1.54.0` (already pinned in `backend/pyproject.toml` by Phase 1) | Supervisor + Gig Triage specialist `Agent` objects, `@tool` decorator, `structured_output_model`, `.as_tool(delegate=True)` | Already the project's locked framework version; re-confirmed still current on PyPI in this pass `[VERIFIED: pip index versions strands-agents → 1.54.0 installed == 1.54.0 latest]` |
| `fastapi` | not yet in `backend/pyproject.toml` — add pinned to current stable | `POST /capture`, `GET /engagements/{id}` | STACK.md's already-approved choice; confirmed current on PyPI this pass: `0.141.1` `[VERIFIED: pip index versions fastapi]` — pin `>=0.141,<0.142` or similar exact pin matching the other Phase-1 pins' style |
| `pydantic` | `>=2.13,<3` (already pinned) | `JobSlice`/`TriageSlice` reused directly as request/response + `structured_output_model` schema | Already the project's schema layer (Phase 1); no change needed |
| `uvicorn[standard]` | not yet in `backend/pyproject.toml` — add pinned | Local ASGI server to run `backend/api.py:app` | STACK.md's already-approved dev server; confirmed current: `0.52.4` `[VERIFIED: pip index versions uvicorn]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | already installed globally (`0.28.1`), add to `backend/pyproject.toml` `dev` extra | `fastapi.testclient.TestClient` depends on `httpx` being importable | Needed the moment any FastAPI test imports `TestClient` |
| `pytest` | already pinned (Phase 1) | Test runner for all new Phase 3 test files | Reuse `backend/pyproject.toml`'s existing `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["."]`) — no new config needed |
| `botocore` (transitive via `boto3`) | already pinned (`>=1.43,<2`) | `ClientError`/`NoCredentialsError`/`BotoCoreError` exception types for the fail-fast 503 mapping | Already imported by Phase 1's `scripts/smoke_test_bedrock_connectivity.py` — reuse that exact exception taxonomy rather than re-deriving it |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reading the tool-result content block directly from `supervisor.messages` | `delegate=True` and parsing `str(supervisor_result)` as the sole extraction mechanism | Verified-compatible with Bedrock (see below), and slightly less code — but ties the merge's correctness to the `AgentDelegation` plugin's internal `end_turn`/`_to_content_blocks` behavior (JSON-serialized-to-**text**, not a native `json` block), which is a less direct/more implicit dependency than reading the tool-result block. Recommend using `delegate=True` for the latency win but keeping the tool-result-block read as the actual merge mechanism (belt-and-suspenders; it works with or without delegation firing). |
| A brand-new `TriageResult` Pydantic model | Reusing `TriageSlice` (`models/engagement_record.py`) directly as `structured_output_model` | `TriageSlice` already has exactly `verdict: Literal["apply","skip"]`, `score: float`, `reasoning: str` `[VERIFIED: backend/models/engagement_record.py:25-28]` — Phase 3's `/capture` payload is already-structured per PRD §6.1 ("Extension POSTs **structured** job data to backend /capture" `[VERIFIED: docs/PRD.md:29]`), so no `extracted_fields`/free-text-extraction step exists yet (that's Phase 2's `extract_job_fields`, TRI-01, explicitly deferred) — a new model would just duplicate `TriageSlice` |
| Async FastAPI route handlers + `httpx.AsyncClient`/`ASGITransport` | Sync `def` route handlers + `fastapi.testclient.TestClient` | Strands' `Agent.__call__` is a **synchronous, blocking** call (`response = agent("text")`, per STACK.md §1 and Phase 1's own scripts) — there is no async I/O to gain from async route handlers in this phase, and sync `TestClient` is simpler to wire than `httpx.AsyncClient(transport=ASGITransport(...))` `[CITED: fastapi.tiangolo.com/advanced/async-tests via WebSearch]` |

**Installation (add to `backend/pyproject.toml`'s `dependencies` + `dev` extras, and `backend/requirements.txt`):**
```bash
pip3 install --user "fastapi>=0.141,<0.142" "uvicorn[standard]>=0.52,<0.53" httpx
```
Reuse Phase 1's exact install workaround (`pip3 install --user ...`) — the plan's own SUMMARY.md recorded that a system-level `pip3 install` failed on a Debian-managed `PyJWT` conflict, and `--user` was the fix that let `python -m pytest` resolve everything without venv activation.

**Version verification:** confirmed via `pip index versions <pkg>` in this sandbox — `strands-agents` 1.54.0 (installed == latest), `fastapi` 0.141.1 latest (not yet installed), `uvicorn` 0.52.4 (installed, latest), `httpx` 0.28.1 (installed, latest). `[VERIFIED: pip index versions, run 2026-09-02]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| `fastapi` | PyPI | published-at 2026-07-29 per registry metadata (long-lived project; this is a recent *release*, not project age) | unknown (seam had no download-count signal in this sandbox) | `github.com/fastapi/fastapi` | SUS (`unknown-downloads` only) | Approved — already recommended in STACK.md (an earlier, separately-vetted research pass); no other risk signal (real repo, not deprecated, no postinstall script) |
| `uvicorn` | PyPI | published-at 2026-08-19 (recent release) | unknown | `github.com/Kludex/uvicorn` | SUS (`too-new`, `unknown-downloads`) | Approved — same rationale; `Kludex` is the current maintainer's real GitHub handle for uvicorn, matches training knowledge |
| `httpx` | PyPI | published-at 2024-12-06 | unknown | `github.com/encode/httpx` | SUS (`unknown-downloads` only) | Approved — `encode` org is the well-known maintainer of httpx/starlette-adjacent projects |
| `pytest-asyncio` | PyPI | published-at 2026-05-26 | unknown | `github.com/pytest-dev/pytest-asyncio` | SUS (`unknown-downloads` only) | **Not needed this phase** — recommend sync `TestClient` instead (see Alternatives Considered); do not add this dependency unless a later phase needs true async testing |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `fastapi`, `uvicorn`, `httpx` — all three verdicts are driven entirely by `unknown-downloads` (this sandbox's package-legitimacy checker could not fetch a download-count signal), not by any authenticity red flag (no missing repo, no postinstall script, no deprecation). All three are also STACK.md's own already-approved recommendations from an earlier, separately-conducted research pass, not newly hallucinated names in this pass. **Nonetheless, per protocol, the planner must add a `checkpoint:human-verify` task before the install step for `fastapi` and `uvicorn`** (the two not-yet-installed packages) so a human confirms the exact pin before it lands in `requirements.txt`.

*Package names in this table were carried over from STACK.md's earlier recommendation (ultimately training-data-informed), not independently re-discovered via WebSearch in this pass — tag `[ASSUMED]` on the package **names**; the version/registry-existence facts are `[VERIFIED: pip index versions]`.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLIENT (curl / future extension)                                    │
│   POST /capture {title, description, budget?, client_stats?}        │
└───────────────────────────────┬───────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ backend/api.py  (FastAPI — sole writer, D-05)                       │
│  1. Validate body as JobSlice (Pydantic)                            │
│  2. record = EngagementRecord(job=JobSlice(...))                    │
│  3. triage_result = triage_runner(record.job)   ◄── DI seam ─────┐  │
│  4. record.triage = triage_result  (typed, verbatim — no re-authoring)│
│  5. store.create(record)                                          │  │
│  6. return {engagement_id, verdict, score, reasoning}              │  │
└──────────────┬──────────────────────────────────────────┬────────┘  │
               │ on Bedrock ClientError/NoCredentialsError │           │
               ▼ (live path only)                          ▼           │
   HTTPException(503, readable, non-leaking)      store.create(record) │
                                                    (FileEngagementStore)│
┌────────────────────────────────────────────────────────────────────┐│
│ backend/triage_runner.py — the D-03 seam, env-flag-selected         ││
│                                                                      ││
│  TRIAGE_BACKEND=placeholder (default)   │  TRIAGE_BACKEND=supervisor │
│  ─────────────────────────────────────  │  ────────────────────────  │
│  placeholder_kill_switch_check(job)     │  supervisor(prompt)        │
│  called as a PLAIN PYTHON FUNCTION      │  → real Bedrock call       │
│  (@tool decorator preserves normal      │  → routes to gig_triage_   │
│  callability) — NO Agent invocation,    │    agent tool              │
│  NO Bedrock, fully deterministic        │  → extract_triage_result() │
│                                          │    reads the toolResult    │
│                                          │    content block verbatim │
└──────────────────────────────────────────┴────────────────────────┘│
                                                                       │
┌──────────────────────────────────────────────────────────────────┐ │
│ backend/agents/supervisor.py + gig_triage_agent.py (D-01)         │ │
│  Two distinct strands.Agent instances — constructed unconditionally│ │
│  (offline-safe, no network call at construction) so D-06(a)/(d)   │ │
│  pass without credentials. Only INVOKING them needs Bedrock.      │ │
└────────────────────────────────────────────────────────────────────┘│
                                                                        │
                    ┌───────────────────────────────────────────────────┘
                    ▼
        GET /engagements/{id}  →  store.get(UUID)  →  404 if None
```

### Recommended Project Structure

```
backend/
├── api.py                       # NEW — FastAPI app, /capture, /engagements/{id}
├── triage_runner.py              # NEW — DI seam (D-03): Protocol + 2 impls, env-selected
├── agents/
│   ├── __init__.py               # existing (Phase 1 placeholder)
│   ├── supervisor.py             # NEW — build_supervisor(): Agent wrapping gig_triage tool
│   └── gig_triage_agent.py       # NEW — build_gig_triage_agent(): Agent + structured_output_model
├── tools/
│   ├── __init__.py               # existing (Phase 1 placeholder)
│   └── placeholder_triage.py     # NEW — @tool deterministic function (D-03/D-04), callable directly
├── models/
│   └── engagement_record.py      # UNCHANGED — TriageSlice reused as the typed contract
├── store/                        # UNCHANGED (Phase 1)
├── tests/
│   ├── test_api_capture.py       # NEW — API-01
│   ├── test_api_engagements.py   # NEW — API-02
│   ├── test_triage_runner.py     # NEW — D-03/D-06(b)
│   └── test_supervisor_wiring_phase3.py  # NEW — D-01/D-06(a)(d), extends Phase 1's pattern
├── pyproject.toml                # MODIFIED — add fastapi/uvicorn/httpx
└── requirements.txt              # MODIFIED — same additions
```

### Structure Rationale

- `triage_runner.py` sits at `backend/` top level, **not** under `agents/` or `tools/` — the existing AST-based single-writer test (`backend/tests/test_single_writer.py`) scans exactly `backend/agents/` and `backend/tools/` for store imports `[VERIFIED: backend/tests/test_single_writer.py — file exists from Phase 1, confirmed via find]`. `triage_runner.py` must never import the store either (only `api.py` does, per D-05), but keeping it outside the scanned directories avoids ambiguity about whether it's "an agent module."
- `placeholder_triage.py`'s function is the **single source of truth** for the deterministic rule — both the offline/test/default path (called directly as a plain function) and the live/demo path (registered as a tool on the specialist `Agent`) call the *same* function body, so there is no risk of the two paths drifting apart.

### Pattern 1: Typed-Channel Merge (ORC-02) — read the tool-result content block directly

**What:** After invoking `supervisor(prompt)`, walk `supervisor.messages` for the assistant message whose `content` contains a `toolResult` block matching the Gig Triage tool's `toolUseId`, and read `content[0]["json"]` — the specialist's `result.structured_output.model_dump(mode="json")` dict, emitted **before** any delegate/re-authoring logic runs.

**Why this works (read directly from the installed package, not docs):**
- `strands/agent/_agent_as_tool.py` (`_AgentAsTool.stream()`), lines 256-263:
  > ```python
  > if result.structured_output:
  >     yield ToolResultEvent(
  >         {
  >             "toolUseId": tool_use_id,
  >             "status": "success",
  >             "content": [{"json": result.structured_output.model_dump(mode="json")}],
  >         }
  >     )
  > elif self._delegate:
  >     ...
  > ```
  `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/agent/_agent_as_tool.py:256-263]` (this sandbox's installed `strands-agents==1.54.0`). This branch is checked **before** the `delegate` branch — so setting `structured_output_model` on the specialist `Agent`'s constructor guarantees a native `json` content block regardless of whether `delegate=True` is also set.
- The exact `ToolResult`/`ToolResultContent` shapes read here:
  > ```python
  > class ToolResultContent(TypedDict, total=False):
  >     json: Any
  >     text: str
  > class ToolResult(TypedDict):
  >     content: list[ToolResultContent]
  >     status: ToolResultStatus
  >     toolUseId: str
  > ```
  `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/types/tools.py:82-113]`
- And the message-level wrapper:
  > `toolResult: ToolResult` — "The result for a tool request that a model makes."
  `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/types/content.py:90,103]`

**Example (FastAPI-side extraction):**
```python
# backend/api.py (excerpt) — Source: strands/agent/_agent_as_tool.py:256-263,
# strands/types/tools.py:82-113, strands/types/content.py:90,103 (this sandbox's installed package)
from models.engagement_record import TriageSlice

def extract_triage_result(supervisor_messages: list[dict]) -> TriageSlice:
    for message in supervisor_messages:
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            for content_block in block["toolResult"].get("content", []):
                if "json" in content_block:
                    return TriageSlice.model_validate(content_block["json"])
    raise RuntimeError("gig_triage_agent tool result not found in supervisor trace")
```
This function never inspects the Supervisor's own final text answer — satisfying D-02's "not by parsing the Supervisor's prose" requirement structurally, not by convention.

### Pattern 2: `delegate=True` — verified compatible with `BedrockModel`

**What:** `.as_tool(delegate=True)` makes the orchestrator's own turn end immediately on a successful specialist call, using the specialist's content as the final answer (skips an extra LLM round-trip). Docs describe this as incompatible with "stateful models that manage conversation state server-side" without naming which providers qualify `[CITED: strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/ via WebFetch]`.

**Resolved via source read:**
> ```python
> @property
> def stateful(self) -> bool:
>     """Whether the model manages conversation state server-side.
>     Returns: False by default. Model providers that support server-side state should override this."""
>     return False
> ```
`[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/models/model.py:182-189]` — and `strands/models/bedrock.py` contains **no** `stateful` override `[VERIFIED: grep -n "stateful" strands/models/bedrock.py → no match]`. Therefore `BedrockModel(...).stateful == False`, and the `AgentDelegation` plugin's own guard (`if agent.model.stateful: has_delegation_tool = ...; raise ValueError(...)`) `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/agent/_agent_delegation.py:99-110]` will **not** fire for this project's Bedrock-backed Supervisor.

**Constraint that DOES apply (verified, not just docs):** a turn calling a delegated tool must call **only** that tool — the plugin's `_on_before_tools` hook cancels the batch if a delegation tool is mixed with any other tool call in the same turn `[VERIFIED: _agent_delegation.py:121-139]`. Phase 3 has exactly one specialist tool registered on the Supervisor, so this constraint is trivially satisfied; it becomes relevant again in Phase 6 (3 specialists) — but since each `/advance` call is already scoped to a single stage (per ARCHITECTURE.md's Data Flow), only one specialist tool is ever offered per Supervisor call anyway.

**Example:**
```python
# backend/agents/supervisor.py — Source: strands/agent/_agent_as_tool.py docstring
# (this sandbox's installed package) + strands/models/model.py:182-189 (stateful default)
from strands import Agent
from agents.gig_triage_agent import build_gig_triage_agent

def build_supervisor() -> Agent:
    triage_agent = build_gig_triage_agent()
    triage_tool = triage_agent.as_tool(
        name="gig_triage_agent",
        description="Run the Gig Triage specialist (placeholder budget/keyword gate; "
                     "Phase 2 will replace with extract_job_fields/kill_switch_check/llm_scorecard). "
                     "Call this whenever a triage verdict is needed for a job.",
        delegate=True,  # verified-compatible: BedrockModel.stateful == False
    )
    return Agent(
        system_prompt="You route every triage request to the gig_triage_agent tool. Never answer yourself.",
        tools=[triage_tool],
    )
```

### Pattern 3: `structured_output_model` — modern API (the old `.structured_output()` method is DEPRECATED)

**What:** Pass `structured_output_model=YourPydanticModel` as an invocation (or constructor) kwarg; read the validated result off `AgentResult.structured_output`.

> "Agent.structured_output method is deprecated. You should pass in `structured_output_model` directly into the agent invocation." `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/agent/agent.py:1010-1011,1041-1042]`
> `AgentResult.structured_output: BaseModel | None = None  # "Parsed structured output when structured_output_model was specified."` `[VERIFIED: /root/.local/lib/python3.11/site-packages/strands/agent/agent_result.py:29,40]`
> Constructor also accepts a **default**: `self._default_structured_output_model = structured_output_model` at `Agent.__init__` `[VERIFIED: strands/agent/agent.py:364]` — set once, applies to every invocation (including via `.as_tool()`, which does not itself pass `structured_output_model` at call time — it relies on this constructor default) `[VERIFIED: strands/agent/_agent_as_tool.py:225 — calls self._agent.stream_async(prompt, cancel_signal=cancel_signal) with no structured_output_model kwarg]`.

**Example (specialist construction — construction-only, no network call):**
```python
# backend/agents/gig_triage_agent.py — Source: strands/agent/agent.py:210,364 (structured_output_model
# constructor default), strands/agent/agent_result.py:29,40 (result.structured_output)
from strands import Agent
from strands.models import BedrockModel
from models.engagement_record import TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check
import os

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")

def build_gig_triage_agent() -> Agent:
    """D-04: PLACEHOLDER Gig Triage specialist — Phase 2 stand-in.
    Wires a real BedrockModel + structured_output_model so the *shape* Phase 2
    will fill is exercised end-to-end; the triage logic itself is deterministic."""
    return Agent(
        name="gig_triage_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Gig Triage specialist (Phase 2 placeholder). Call "
            "placeholder_kill_switch_check with the job's budget and description, "
            "then return its result."
        ),
        tools=[placeholder_kill_switch_check],
        structured_output_model=TriageSlice,
    )
```

### Anti-Patterns to Avoid

- **Prompt-engineering "please repeat the JSON verbatim" as the merge mechanism:** ARCHITECTURE.md's own Pattern 2/Anti-Pattern 2 flags this as a fallback *only if the SDK version lacks a better mechanism* — it does not, in this pinned version (see Pattern 1/2/3 above). Do not build a system-prompt-based verbatim-repetition instruction as the primary mechanism; it is non-deterministic across runs (LLM nondeterminism, PITFALLS.md Pitfall 7) where the tool-result-block read is not.
- **Skipping the real `Agent` construction for the placeholder:** D-01 requires two distinct `Agent` instances to exist in code even while the triage *logic* is deterministic — do not collapse `build_supervisor()`/`build_gig_triage_agent()` into a single function that only runs the placeholder Python function; keep both present and offline-testable (construction only), per Phase 1's precedent (`build_supervisor()` in `smoke_test_agents_as_tools.py` is tested for construction, `main()` is manual-only).
- **Making `agent.tool.tool_name(param=value)` the deterministic-path mechanism:** direct tool invocation via the `Agent`'s tool accessor still goes through the `Agent` instance's tool-invocation machinery and message-history recording `[CITED: WebSearch summary of strandsagents.com docs — not independently source-read this pass]`; simpler and more clearly "no Agent at all" for the offline path is calling the underlying plain Python function directly (the `@tool` decorator explicitly preserves this: "Still works as a normal function when called directly with arguments" `[VERIFIED: strands/tools/decorator.py:758]`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bedrock exception → readable diagnosis | A new exception-taxonomy/branching block in `api.py` | Reuse/refactor Phase 1's exact taxonomy from `backend/scripts/smoke_test_bedrock_connectivity.py` (`NoCredentialsError`, `ClientError` branched on `Error.Code` incl. `AccessDeniedException`/`UnrecognizedClientException`/`ValidationException`/`ThrottlingException`, `ConnectTimeoutError`/`ReadTimeoutError`, `EndpointConnectionError`, `ModelThrottledException`, `ContextWindowOverflowException`, `BotoCoreError` catch-all, final `Exception` safety net) `[VERIFIED: backend/scripts/smoke_test_bedrock_connectivity.py:24-120 — already tested by backend/tests/test_bedrock_smoke.py]` | Already written, already tested, already proven to never leak the `proxy-injected` credential literal in this exact sandbox — recommend extracting the branching logic into a shared `map_bedrock_error(exc) -> tuple[int, str]` helper both the script and `api.py`'s exception handler import, rather than duplicating the `except` chain |
| Typed pass-through from specialist to caller | A hand-rolled string-parsing/regex extraction of JSON from the Supervisor's final text answer | `structured_output_model` + reading the `toolResult` content block (Pattern 1/3 above) | Regex/prose-parsing is exactly the "Supervisor re-authoring" failure mode D-02 exists to prevent — a native typed content block is deterministic where text-parsing is not |
| Path-traversal protection on `engagement_id` | Custom string sanitization in `api.py`'s `GET /engagements/{id}` handler | Type the FastAPI path param as `UUID` directly (`engagement_id: UUID`) — FastAPI validates/parses it before the handler body runs, and `FileEngagementStore._path()` already raises `TypeError` on anything that isn't a `UUID` instance | `[VERIFIED: backend/store/file_engagement_store.py:33-38 — "if not isinstance(engagement_id, UUID): raise TypeError(...)"]` — this protection already exists structurally; re-implementing it in the API layer would be redundant, not defense-in-depth |
| Singleton store wiring | A module-level mutable global imported ad hoc across files | `Depends(get_store)` with a module-level singleton instance behind the dependency function; override via `app.dependency_overrides[get_store] = lambda: test_store` in tests | `[CITED: fastapi.tiangolo.com/tutorial/dependencies via WebFetch — "You just pass it to Depends and FastAPI knows how to do the rest"]` — this is FastAPI's own documented idiom, and it is what lets `backend/tests/conftest.py`'s existing `file_store` fixture (bound to `tmp_path`) be reused as an override rather than needing a parallel test-only construction path |

**Key insight:** every "hand-roll risk" in this phase already has either (a) a working, tested Phase 1 solution to reuse (Bedrock exceptions, UUID path-traversal), or (b) a source-verified SDK mechanism that makes hand-rolling unnecessary (typed pass-through). The temptation to hand-roll comes from *not knowing* these mechanisms exist — which is exactly what this research pass resolved by reading the installed package source directly rather than relying on (sometimes incomplete) public docs.

## Common Pitfalls

### Pitfall 1: Assuming `structured_output_model` alone prevents Supervisor re-authoring
**What goes wrong:** Setting `structured_output_model=TriageSlice` only on the specialist Agent's constructor guarantees `result.structured_output` is populated *for the specialist's own call* — but if the specialist is wrapped with plain `.as_tool()` (no `delegate=True`) and the merge code naively reads `str(supervisor_result)` (the Supervisor's own final answer) instead of the tool-result content block, the Supervisor's LLM can still paraphrase in that final answer even though the underlying tool result was clean JSON.
**Why it happens:** It's easy to conflate "the specialist returned structured data" with "the thing my code reads is that structured data" — they are different objects (`tool_result` vs. `supervisor_result.message`) unless `delegate=True` also fires and `merge` reads the delegation-populated final message specifically.
**How to avoid:** Merge code must read `supervisor.messages`' `toolResult` content block directly (Pattern 1), not `supervisor_result`/`str(supervisor_result)`. This works regardless of `delegate`.
**Warning signs:** The merged `TriageSlice.reasoning` text differs between two runs with an identical placeholder/fixture input — a sign the merge code is reading the Supervisor's re-authored prose, not the specialist's raw structured output.

### Pitfall 2: Making the specialist `Agent`'s construction require Bedrock credentials
**What goes wrong:** `BedrockModel(...)` + `Agent(model=..., structured_output_model=...)` construction performs **no** network call — confirmed by Phase 1 both in code comments and in `test_agents_as_tools_smoke.py` passing with placeholder credentials `[VERIFIED: backend/tests/test_agents_as_tools_smoke.py — passes in this sandbox with AWS_ACCESS_KEY_ID=proxy-injected]`. If Phase 3's `build_supervisor()`/`build_gig_triage_agent()` accidentally trigger any construction-time validation call (e.g., an eager credential check), D-06(a)/(d)'s offline-construction tests would fail in CI/this sandbox.
**How to avoid:** Keep `build_supervisor()`/`build_gig_triage_agent()` side-effect-free at construction (matching Phase 1's precedent exactly) — only `agent(prompt)`/`stream_async(...)` invocation touches the network.

### Pitfall 3: TriageSlice vs. "extracted_fields" scope confusion
**What goes wrong:** TRI-04 (Phase 2's requirement) describes the Gig Triage Agent's full eventual output as `{verdict, score, reasoning, extracted_fields}` — but `extracted_fields` has no home in `TriageSlice` `[VERIFIED: backend/models/engagement_record.py:25-28 — TriageSlice has only verdict/score/reasoning]`; it belongs in `JobSlice` (`title`/`description`/`budget`/`client_stats`) `[VERIFIED: backend/models/engagement_record.py:18-22]`. A planner who tries to build a single "TriageResult" model covering both slices in Phase 3 will either duplicate `JobSlice`'s fields unnecessarily or design a merge that doesn't match either existing model.
**Why it happens:** TRI-04's wording describes Phase 2's eventual full pipeline (which includes `extract_job_fields`, TRI-01) — Phase 3's `/capture` already receives a **structured** payload per API-01 and PRD §6.1 ("Extension POSTs structured job data to backend /capture" `[VERIFIED: docs/PRD.md:29]`), so there is no free-text extraction step in Phase 3 at all.
**How to avoid:** Phase 3's placeholder `TriageResult` == `TriageSlice` exactly (verdict/score/reasoning only); no `extracted_fields` merge needed in this phase. Document this scope boundary explicitly in the plan so Phase 2 knows it's adding a `JobSlice`-merge step later, not modifying Phase 3's triage-merge.

### Pitfall 4: `delegate=True` + a mixed-tool turn silently getting cancelled
**What goes wrong:** If a later phase (6) reuses this Supervisor pattern and adds a second tool call in the *same* turn as a delegated call, the `AgentDelegation` plugin cancels the entire batch (`event.cancel = "..."`) rather than raising — this can look like "the tool call silently did nothing" if not specifically tested for.
**How to avoid:** Not a Phase 3 risk (only one specialist tool exists), but document it now so Phase 6's plan doesn't rediscover it the hard way. `[VERIFIED: strands/agent/_agent_delegation.py:121-139]`

## Code Examples

### FastAPI Endpoint Design

```python
# backend/api.py
# Source: fastapi.tiangolo.com/tutorial/dependencies (Depends/dependency_overrides pattern,
# CITED via WebFetch) + backend/models/engagement_record.py (JobSlice/TriageSlice, VERIFIED),
# backend/store/engagement_store.py (EngagementStore.get signature, VERIFIED)
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from models.engagement_record import EngagementRecord, JobSlice
from store.engagement_store import EngagementStore
from store.file_engagement_store import FileEngagementStore
from triage_runner import TriageRunner, get_triage_runner

app = FastAPI()
_store = FileEngagementStore()  # single construction point, per Phase 1's swap seam


def get_store() -> EngagementStore:
    return _store


class CaptureResponse(BaseModel):
    engagement_id: UUID
    verdict: str
    score: float
    reasoning: str


@app.post("/capture", response_model=CaptureResponse)
def capture(
    job: JobSlice,
    store: Annotated[EngagementStore, Depends(get_store)],
    triage_runner: Annotated[TriageRunner, Depends(get_triage_runner)],
) -> CaptureResponse:
    record = EngagementRecord(job=job)
    try:
        record.triage = triage_runner(job)  # typed, verbatim merge (D-02)
    except BedrockUnavailableError as e:  # see "Bedrock Fail-Fast" example below
        raise HTTPException(status_code=503, detail=str(e)) from e
    store.create(record)
    return CaptureResponse(
        engagement_id=record.engagement_id,
        verdict=record.triage.verdict,
        score=record.triage.score,
        reasoning=record.triage.reasoning,
    )


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

### The `TriageRunner` DI Seam (D-03/D-06)

```python
# backend/triage_runner.py
# Source: strands/tools/decorator.py:758 ("Still works as a normal function when called
# directly with arguments", VERIFIED — installed package) for the deterministic-path call;
# extract_triage_result per _agent_as_tool.py:256-263 (VERIFIED) for the live path.
import os
from typing import Protocol

from agents.supervisor import build_supervisor
from models.engagement_record import JobSlice, TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check


class TriageRunner(Protocol):
    def __call__(self, job: JobSlice) -> TriageSlice: ...


def _deterministic_triage_runner(job: JobSlice) -> TriageSlice:
    """D-03: no Agent invocation, no Bedrock — pure Python."""
    return placeholder_kill_switch_check(job.budget, job.description)


def _supervisor_triage_runner(job: JobSlice) -> TriageSlice:
    """Live path: real Supervisor -> Gig Triage Agent via Bedrock (manual-verification path)."""
    supervisor = build_supervisor()
    supervisor(f"Triage this job: {job.model_dump_json()}")
    return extract_triage_result(supervisor.messages)  # Pattern 1 above


def get_triage_runner() -> TriageRunner:
    backend = os.environ.get("TRIAGE_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_triage_runner
    return _deterministic_triage_runner
```

### Bedrock Fail-Fast (reused from Phase 1's exact taxonomy)

```python
# backend/api.py (excerpt) — Source: backend/scripts/smoke_test_bedrock_connectivity.py:24-120
# (VERIFIED, this repo, already tested by backend/tests/test_bedrock_smoke.py)
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


class BedrockUnavailableError(RuntimeError):
    """Readable, non-leaking Bedrock failure — never includes the raw AWS error Message."""


def map_bedrock_error(e: Exception) -> BedrockUnavailableError:
    if isinstance(e, NoCredentialsError):
        return BedrockUnavailableError("no AWS credentials found for Bedrock.")
    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "Unknown")
        return BedrockUnavailableError(f"Bedrock ClientError [{code}] — see the Bedrock console.")
    if isinstance(e, BotoCoreError):
        return BedrockUnavailableError(f"AWS SDK error ({type(e).__name__}) talking to Bedrock.")
    return BedrockUnavailableError(f"unexpected error contacting Bedrock ({type(e).__name__}).")
```

### Testing `/capture` Offline (D-06)

```python
# backend/tests/test_api_capture.py
# Source: fastapi.testclient.TestClient pattern (CITED via WebSearch, fastapi.tiangolo.com/reference/testclient)
from fastapi.testclient import TestClient

from api import app, get_store, get_triage_runner
from triage_runner import _deterministic_triage_runner


def test_capture_creates_record_and_returns_verdict(file_store, monkeypatch):
    app.dependency_overrides[get_store] = lambda: file_store
    app.dependency_overrides[get_triage_runner] = lambda: _deterministic_triage_runner
    client = TestClient(app)

    response = client.post("/capture", json={
        "title": "Build a landing page",
        "description": "Simple static site, no red flags",
        "budget": 500.0,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] in ("apply", "skip")
    app.dependency_overrides.clear()
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Package names `fastapi`/`uvicorn`/`httpx` are legitimate, well-known packages (not slopsquatted) | Standard Stack / Package Legitimacy Audit | Low — these names were carried from STACK.md's earlier, separately-conducted recommendation and match well-known training-data knowledge, but were not independently re-discovered via an authoritative source in *this* pass; if wrong, a malicious package would be pulled in at `pip install` time |
| A2 | Whether `agent.tool.tool_name(...)` direct invocation records to message history in a way that would interfere with the deterministic path if used instead of a plain function call | Anti-Patterns to Avoid | Low — this claim came from WebSearch summary only, not a direct source read; recommend just calling `placeholder_kill_switch_check(...)` as a plain function (verified-safe via decorator.py:758) and avoiding `agent.tool.*` entirely for the deterministic path, sidestepping the need to resolve this uncertainty |
| A3 | FastAPI's exact recommended singleton-DI pattern (`Depends(get_store)` + `app.dependency_overrides`) matches the version that will actually be installed (0.141.1) | Code Examples / Don't Hand-Roll | Low — this is long-stable core FastAPI API surface per WebSearch/WebFetch summary, unlikely to have changed, but not independently fetched against the exact 0.141.1 docs snapshot |

**If this table is empty:** N/A — see above; all three are low-risk/low-impact assumptions with a stated mitigation already built into the recommendation.

## Open Questions

1. **Exact final-message shape when `delegate=True` fires (if the planner wants to use `str(supervisor_result)` as a secondary/fallback read)**
   - What we know: `_agent_delegation.py`'s `_on_after_tools` hook sets `event.end_turn` to JSON-serialized-to-text content blocks (`_to_content_blocks`, verified) when delegation succeeds.
   - What's unclear: whether `event.end_turn` maps 1:1 onto `AgentResult.message["content"]` in exactly the shape assumed, was not traced end-to-end through the event-loop's `end_turn`-handling code in this pass (time-boxed to the load-bearing merge mechanism, Pattern 1, which does not depend on this).
   - Recommendation: don't build the merge logic around `str(supervisor_result)`/`delegate`'s final-message assembly at all — Pattern 1 (reading the `toolResult` block directly) is fully verified and suffices on its own; treat `delegate=True` purely as a latency optimization, not a correctness dependency.

2. **Whether a live Bedrock smoke test of this exact wiring (Supervisor → placeholder-backed Gig Triage Agent, two-invocation trace) has been run against real AWS credentials**
   - What we know: this sandbox has only placeholder credentials (`AWS_ACCESS_KEY_ID=proxy-injected`, no `AWS_REGION` set) — confirmed identical to Phase 1's exact situation.
   - What's unclear: the real trace shape (`supervisor.messages`' tool-result content block) has not been observed against a live, successful Bedrock call in this environment — only construction-time attributes and the installed package's *source code* (not its runtime behavior against live Bedrock) were verified.
   - Recommendation: per D-06, this is explicitly a **manual, human-run verification** — the plan should include a manual verification step identical in spirit to Phase 1's `smoke_test_bedrock_connectivity.py`/`smoke_test_agents_as_tools.py` split, run once by a human with real AWS credentials before the demo recording.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all backend code | ✓ | 3.11.15 | — |
| `strands-agents` | Supervisor/specialist `Agent` construction | ✓ | 1.54.0 (matches Phase 1 pin, still latest) | — |
| `fastapi` | `/capture`, `/engagements/{id}` | ✗ (not yet installed) | — | Install via `pip3 install --user "fastapi>=0.141,<0.142"` (Phase 1's exact workaround pattern) |
| `uvicorn` | Running `backend/api.py:app` locally | ✓ (globally, 0.52.4) | 0.52.4 | Add explicit pin to `backend/pyproject.toml`/`requirements.txt` even though already present |
| `httpx` | `fastapi.testclient.TestClient` | ✓ (globally, 0.28.1) | 0.28.1 | Add explicit pin to `backend/pyproject.toml`'s `dev` extra |
| Real AWS Bedrock credentials | Live Supervisor→specialist invocation (manual-verification path only) | ✗ (`AWS_ACCESS_KEY_ID=proxy-injected`, no `AWS_REGION`) | — | Deterministic placeholder path (`TRIAGE_BACKEND=placeholder`, the default) fully covers automated tests; live path is human-run only, per D-06 |

**Missing dependencies with no fallback:** none — `fastapi` install is a one-line fix, not a blocker.
**Missing dependencies with fallback:** real Bedrock credentials (fallback: deterministic placeholder path + manual human verification, exactly as Phase 1 established).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` (already pinned, `backend/pyproject.toml`) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` — `testpaths=["tests"]`, `pythonpath=["."]` (unchanged, reused from Phase 1) |
| Quick run command | `cd backend && python -m pytest tests/test_api_capture.py tests/test_api_engagements.py -q` |
| Full suite command | `cd backend && python -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| ORC-02 | Typed `TriageSlice` merged verbatim from the tool-result content block, not the Supervisor's prose | unit | `pytest tests/test_supervisor_wiring_phase3.py::test_extract_triage_result_reads_tool_result_block -x` | ❌ Wave 0 |
| ORC-02 | Supervisor constructs offline (no creds) with `gig_triage_agent` tool registered | unit | `pytest tests/test_supervisor_wiring_phase3.py::test_build_supervisor_registers_gig_triage_agent -x` | ❌ Wave 0 |
| API-01 | `POST /capture` creates a record, merges triage, persists, returns verdict — using the deterministic placeholder (no live LLM) | unit | `pytest tests/test_api_capture.py::test_capture_creates_record_and_returns_verdict -x` | ❌ Wave 0 |
| API-01 | `POST /capture` returns 503 (not a raw 500) when the (mocked) supervisor path raises a Bedrock `ClientError` | unit | `pytest tests/test_api_capture.py::test_capture_fails_fast_with_503_on_bedrock_error -x` | ❌ Wave 0 |
| API-02 | `GET /engagements/{id}` round-trips a persisted record | unit | `pytest tests/test_api_engagements.py::test_get_engagement_round_trips -x` | ❌ Wave 0 |
| API-02 | `GET /engagements/{id}` returns 404 for an unknown id | unit | `pytest tests/test_api_engagements.py::test_get_unknown_engagement_returns_404 -x` | ❌ Wave 0 |
| D-03/D-06(b) | Deterministic placeholder produces a stable verdict for a fixed budget+keyword input, called as a plain function (no Agent/Bedrock) | unit | `pytest tests/test_triage_runner.py::test_deterministic_triage_runner_is_pure_python -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_api_capture.py tests/test_api_engagements.py tests/test_triage_runner.py -q`
- **Per wave merge:** `cd backend && python -m pytest -q` (full suite, includes Phase 1's existing tests — must stay green)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_api_capture.py` — covers API-01
- [ ] `backend/tests/test_api_engagements.py` — covers API-02
- [ ] `backend/tests/test_triage_runner.py` — covers D-03/D-06(b)
- [ ] `backend/tests/test_supervisor_wiring_phase3.py` — covers ORC-02/D-01/D-06(a)(d)
- [ ] Framework install: `pip3 install --user "fastapi>=0.141,<0.142" "uvicorn[standard]>=0.52,<0.53" httpx` — add to `backend/pyproject.toml`/`requirements.txt`
- [ ] `backend/tests/conftest.py`'s existing `file_store` fixture is reusable as-is for the new API tests (bound to `tmp_path`, already `[VERIFIED: backend/tests/conftest.py:9-13]`) — no new fixture needed there

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Out of scope for this phase — PROJECT.md/PRD.md §8 explicitly defer auth to the demo/extension phase ("No auth needed for demo; single local API key") `[VERIFIED: docs/PRD.md:43]`; no auth requirement is listed against Phase 3 in REQUIREMENTS.md |
| V3 Session Management | No | No session concept in this stateless REST API |
| V4 Access Control | No | Single-user local demo; no multi-tenant access control in scope |
| V5 Input Validation | Yes | Pydantic (`JobSlice` reused directly as the request body model) validates all `/capture` input at the boundary; `engagement_id: UUID` path-param typing rejects malformed ids before the handler runs |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Path traversal via a crafted `engagement_id` | Tampering | Already closed structurally: `engagement_id` is `UUID`-typed at both the FastAPI path param and the `EngagementStore` interface; `FileEngagementStore._path()` raises `TypeError` on any non-`UUID` `[VERIFIED: backend/store/file_engagement_store.py:33-38]` — do not weaken this by ever accepting `engagement_id: str` anywhere in the new code |
| Credential/secret leakage in a Bedrock error response returned to the API caller | Information Disclosure | Reuse Phase 1's pattern: surface only the exception's *type*/`Error.Code`, never the raw AWS `Message` text or the credential literal, in the `HTTPException(503, ...)` detail `[VERIFIED: backend/scripts/smoke_test_bedrock_connectivity.py:63-64 — "Only the error Code (never the raw Message) is surfaced"]` |
| Oversized/malformed `/capture` payload (e.g. an extremely long `description`) causing resource exhaustion | Denial of Service | Not a locked requirement for this phase; Pydantic validates *types* but not size bounds. Flag as a candidate follow-up (not blocking Phase 3) — no size limit currently exists on `JobSlice.description`/`title` |

## Sources

### Primary (HIGH confidence — read directly from this sandbox's installed `strands-agents==1.54.0` source, and from this repo's own Phase 1 code)
- `/root/.local/lib/python3.11/site-packages/strands/agent/_agent_as_tool.py` — `.as_tool()`/`delegate` mechanics, structured_output-priority ToolResult emission
- `/root/.local/lib/python3.11/site-packages/strands/agent/_agent_delegation.py` — `AgentDelegation` plugin, stateful-model guard, single-call constraint
- `/root/.local/lib/python3.11/site-packages/strands/models/model.py` — `Model.stateful` default (`False`)
- `/root/.local/lib/python3.11/site-packages/strands/models/bedrock.py` — confirmed no `stateful` override (grep, no match)
- `/root/.local/lib/python3.11/site-packages/strands/agent/agent.py` — `structured_output_model` constructor default, deprecation of `.structured_output()`
- `/root/.local/lib/python3.11/site-packages/strands/agent/agent_result.py` — `AgentResult.structured_output`, `__str__` priority order
- `/root/.local/lib/python3.11/site-packages/strands/types/tools.py`, `strands/types/content.py` — `ToolResult`/`ToolResultContent`/`toolResult` message shape
- `/root/.local/lib/python3.11/site-packages/strands/tools/decorator.py` — `@tool`'s `_wrap_tool_result` (dict-with-status/content passthrough vs. `json.dumps`-to-text), normal-callability preservation
- `backend/models/engagement_record.py`, `backend/store/engagement_store.py`, `backend/store/file_engagement_store.py`, `backend/scripts/smoke_test_bedrock_connectivity.py`, `backend/tests/*` — this repo's Phase 1 artifacts
- `docs/PRD.md` §6.1/6.2 — Engagement Record shape, `/capture` structured-payload wording
- `pip index versions strands-agents/fastapi/uvicorn/httpx` (run 2026-09-02) — registry existence + current version

### Secondary (MEDIUM confidence — WebFetch of official strandsagents.com docs, not the installed source)
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/ — three wrapping shapes, delegate mechanism, "stateful models" caveat (provider-agnostic wording)
- https://strandsagents.com/docs/user-guide/concepts/agents/structured-output/ — deprecation notice for `Agent.structured_output()`, confirms modern `structured_output_model=` pattern
- https://fastapi.tiangolo.com/tutorial/dependencies/ — singleton DI pattern, `app.dependency_overrides`

### Tertiary (LOW confidence — WebSearch summaries, not independently fetched in full)
- `agent.tool.tool_name(...)` direct-invocation semantics (name resolution, message-history recording) — not used in the final recommendation (plain function call preferred instead, which IS source-verified)
- FastAPI `TestClient`/`httpx.AsyncClient`+`ASGITransport` testing patterns — sync `TestClient` recommended, matching Strands' synchronous `Agent.__call__`
- botocore `ClientError` → FastAPI `HTTPException` mapping idiom (general pattern; this project's specific exception taxonomy is instead reused verbatim from Phase 1, which IS source-verified in this repo)
- Package-legitimacy `SUS` verdicts for `fastapi`/`uvicorn`/`httpx`/`pytest-asyncio` — driven by `unknown-downloads` signal gaps in this sandbox, not by an independent authenticity finding

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via `pip index versions`, `strands-agents` version reused from an already-complete Phase 1
- Architecture (typed-channel merge, delegate compatibility): HIGH — read directly from the installed package's source code, not from docs or training memory
- FastAPI/pytest idioms: MEDIUM — stable, well-established API surface, WebSearch/WebFetch-verified but not independently confirmed against the exact 0.141.1 release notes
- Pitfalls: HIGH for Strands-specific pitfalls (source-verified), MEDIUM for generic FastAPI/testing pitfalls

**Research date:** 2026-09-02
**Valid until:** 7 days for the Strands-specific findings (fast-moving SDK — re-verify against the installed package if `strands-agents` is upgraded past 1.54.0 before this phase is executed); 30 days for the FastAPI/pytest findings (stable surface)

---
*Research for: Phase 3 - Supervisor Wiring + /capture Endpoint*
*Researched: 2026-09-02*
