# Stack Research

**Domain:** Greenfield multi-agent backend (AWS Strands Agents SDK) + FastAPI + Claude/Bedrock + Manifest V3 Chrome extension
**Researched:** 2026-09-01
**Confidence:** HIGH on Strands core API, Bedrock wiring, FastAPI/CORS, MV3 permissions — MEDIUM on the exact multi-agent pattern recommendation (fast-moving SDK, docs are thin on cross-pattern trade-offs) — LOW/UNVERIFIED on AgentCore Memory (community-maintained integration, explicitly marked unstable by its own docs)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `strands-agents` | ≥1.0 (latest verified: 1.54.0, released 2026-08-27) | Core agent framework — `Agent` class, model providers, tool system, multi-agent orchestrators | Official AWS-sponsored SDK, the hackathon's required framework; API has stabilized past 1.0 (pre-1.0 docs at `strandsagents.com/0.1.x/...` are stale and diverge from current API — don't follow them) |
| `strands-agents-tools` | ≥0.2 | Optional prebuilt tools (`calculator`, `http_request`, `retrieve`, etc.) | Not required for this project's custom tools, but useful for `check_invoice_status`-style date/file utilities if it saves time |
| FastAPI | latest stable (≥0.115) | HTTP backend hosting the supervisor + sub-agents, exposes `/capture`, `/engagements/{id}`, `/engagements/{id}/advance` | Already specified in PROJECT.md; async-native, pairs cleanly with Pydantic for the Engagement Record schema and request/response models |
| Pydantic | v2 (FastAPI ≥0.100 uses v2 by default) | Request/response models, Engagement Record schema validation, and Strands `structured_output()` schemas | Shared schema layer between FastAPI I/O and Strands' structured-output tool-calling mechanism — one model definition serves both |
| `boto3` | latest | Underlying AWS SDK Strands' `BedrockModel` uses for Bedrock Runtime calls, and for AgentCore if pursued | Pulled in transitively by `strands-agents[bedrock]` extras / `bedrock-agentcore`; pin explicitly if you need session/credential control |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bedrock-agentcore[strands-agents]` | latest | AgentCore Memory session manager for cross-stage Engagement Record persistence | Only if pursuing the AgentCore stretch goal — see caveats below |
| `python-multipart` | latest | Form/file upload support in FastAPI (if the extension ever posts non-JSON) | Only if `/capture` needs anything beyond JSON body |
| `uvicorn[standard]` | latest | ASGI server to run the FastAPI app locally | Standard FastAPI dev/run server |
| `pytest` + `httpx` | latest | Testing the FastAPI endpoints and agent tool functions in isolation | `httpx.AsyncClient` is FastAPI's recommended test client for async endpoints |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uvicorn --reload` | Local dev server for FastAPI | Point at `backend/api.py:app` |
| AWS CLI / `aws configure` | Local Bedrock credentials | Strands' `BedrockModel` resolves credentials via the standard boto3 chain (env vars → shared config → instance role) — no Strands-specific auth needed |
| Chrome "Load unpacked" (`chrome://extensions`) | Load the MV3 extension for local testing | Needed to get the extension's actual `chrome-extension://<id>` origin for CORS/manifest configuration |

## Installation

```bash
# Core
pip install strands-agents fastapi "uvicorn[standard]"

# Bedrock model provider (bundled in strands-agents, no extra needed for Bedrock specifically
# — but boto3 must be present and AWS-credentialed)
pip install boto3

# Optional prebuilt Strands tools
pip install strands-agents-tools

# Stretch: AgentCore Memory
pip install "bedrock-agentcore[strands-agents]"

# Dev/test
pip install pytest httpx
```

No `requirements.txt` version pins are prescribed here beyond "current at build time" — pin exact versions once you run `pip install` and freeze, since Strands is releasing frequently (1.54.0 as of Aug 27, 2026).

## Verified API Specifics (source of truth, not memory)

### 1. Strands Agents SDK — package, install, minimal Agent

- PyPI package: **`strands-agents`** (import name is `strands`, not `strands_agents` — classic PyPI-name/import-name split). Current version verified on PyPI: **1.54.0** (2026-08-27). Requires Python 3.10+.
- Minimal construction:
```python
from strands import Agent
agent = Agent(tools=[...])
response = agent("your message")
```
- Two calling conventions: natural-language (`agent("text")`) and direct tool invocation (`agent.tool.tool_name(param=...)`).
- Model defaults to Bedrock's Claude if `model` is omitted (Strands ships Bedrock as the default provider) — but for this project, pass an explicit `BedrockModel` (see §4) rather than relying on the default, so the model ID is visible and controlled in code.

### 2. Supervisor → specialist pattern — RECOMMENDATION: **Agents-as-Tools**

Current Strands (post-1.0) supports four documented multi-agent shapes:

| Pattern | Import | Control flow | Fit for this project |
|---|---|---|---|
| **Agents-as-Tools** | `from strands import Agent, tool` (a specialist `Agent` is wrapped in an `@tool`-decorated function and passed into the supervisor's `tools=[...]`) | Supervisor's LLM decides which specialist tool to call, in normal tool-calling loop | **Recommended** |
| Graph | `from strands.multiagent import GraphBuilder` (not fully verified here — inferred from docs structure; verify signature before use) | Developer-defined directed graph, deterministic edges | Overkill: no branching/looping needed, three stages run in a fixed sequence already |
| Swarm | `from strands.multiagent import Swarm` | Agents autonomously hand off to each other; model-driven, non-deterministic entry/exit | Wrong fit: the PRD needs deterministic, judgeable escalation points, not free-form handoff |
| Workflow | Plain Python chaining of agent calls (code-level DAG, not an SDK primitive) | Fully developer-controlled | Viable fallback but forfeits the "genuine Strands multi-agent orchestration" visible in code that judges are scored on |

**Why Agents-as-Tools wins here:** the PRD explicitly requires "genuine multi-agent Strands orchestration... visible in both the architecture diagram and the code — not a single wrapped LLM call," while also requiring deterministic staged control (`/engagements/{id}/advance` explicitly steps the Engagement Record through stages under FastAPI's control, not the LLM's). Agents-as-Tools gives you both: the **supervisor Agent** is a real Strands `Agent` whose `tools=[gig_triage_agent, proposal_contract_agent, ops_agent]` list is genuine multi-agent delegation (satisfies judging), while your FastAPI route handlers — not agent-internal routing — decide *when* to call the supervisor for each stage (satisfies the deterministic-demo requirement). Swarm's model-driven handoff would fight against the fixture-driven, repeatable-demo constraint; Graph's benefit (branching/loops) isn't needed because your three stages are linear and externally triggered by `/advance`.

Verified code shape (from official docs, `agents-as-tools` page):
```python
from strands import Agent, tool

@tool
def gig_triage_agent(job_text: str) -> str:
    """Run triage on a pasted job posting. Returns verdict/score/reasoning as JSON text."""
    agent = Agent(
        system_prompt="You are the Gig Triage specialist...",
        tools=[extract_job_fields, kill_switch_check, llm_scorecard],
    )
    return str(agent(job_text))

supervisor = Agent(
    system_prompt="You orchestrate freelance engagement stages...",
    tools=[gig_triage_agent, proposal_contract_agent, ops_agent],
)
```
Note the specialist tool function returns `str` (or a `dict`/`ToolResult`, see §3) — the supervisor sees it as any other tool result, then synthesizes/relays it.

**What NOT to use:** don't build this on `strands.multiagent.Swarm` expecting deterministic staged output — its entry/exit and handoff count are LLM-decided per run, which breaks the "runs deterministically for a ≤5-minute demo" constraint. Don't hand-roll your own routing string-matching on agent names — Strands' tool-calling already does this via the model's function-calling, so a manual dispatcher duplicates/fights the SDK.

### 3. Defining tools — `@tool` decorator, typed results

- Import: `from strands import tool`.
- Decorate a plain Python function; the type hints and docstring become the tool's schema (name, description, args) presented to the model:
```python
@tool
def kill_switch_check(budget: float, red_flags: list[str], client_hire_rate: float) -> dict:
    """Deterministic gate: fails if budget below floor, red-flag keywords present, or hire rate too low."""
    ...
    return {"passed": True, "reasons": []}
```
- Return handling: a plain string is auto-wrapped as `{"text": str(result)}`; a `dict` matching the `ToolResult` TypedDict shape (`{"status": "success"|"error", "content": [...], "toolUseId": ...}`) is used as-is; raised exceptions are converted to an error-status `ToolResult` automatically. For this project's tools (`extract_job_fields`, `llm_scorecard`, `check_scope_creep`, etc.) return a plain `dict` of your Engagement-Record-shaped fields — Strands' auto-wrapping handles the rest, no need to hand-construct `ToolResult` objects.
- For getting a **validated Pydantic object** back from an agent's final answer (as opposed to a tool call), use `agent.structured_output(YourPydanticModel, prompt)` — internally Strands registers your Pydantic model as a tool spec and validates the model's output against it. This is the right mechanism for forcing the Gig Triage Agent's final `{verdict, score, reasoning, extracted_fields}` into a strict schema you can drop directly into the Engagement Record. Recommend defining that response shape as a Pydantic `BaseModel` shared between the Strands call and the FastAPI response model.
- An agent calls a tool automatically as part of its normal loop once the tool is in its `tools=[...]` list — no separate registration step. Direct/manual invocation for testing: `agent.tool.tool_name(param=value)`.

### 4. Claude via Bedrock — model provider wiring

- Import: `from strands.models import BedrockModel`.
- Construction:
```python
from strands import Agent
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",  # or "global.anthropic.claude-sonnet-4-6"
    region_name="us-east-1",
    temperature=0.3,
)
agent = Agent(model=bedrock_model)
```
- Model ID: use a Bedrock **inference profile ID** (the `us.` or `global.` prefixed form), not the bare `anthropic.claude-...` foundation-model ID, for cross-region throughput — verify the exact current Claude model slug against your AWS account's enabled Bedrock models at build time (model IDs get versioned/renamed; don't hardcode from memory — confirm in the Bedrock console's "Model access" page before shipping).
- Credentials/region resolve through the standard boto3 chain: explicit `region_name` in `BedrockModel(...)` → boto3 session → `AWS_REGION` env var → default (`us-west-2`). For local dev, `aws configure` or exported `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` is enough; no Strands-specific credential mechanism exists.
- To pass a custom boto3 session (e.g., assumed role, non-default profile): `BedrockModel(model_id=..., boto_session=boto3.Session(...))`.
- **What NOT to use:** don't pass a raw model-id string directly to `Agent(model="...")` for production code even though it's supported — it hides region/credential/temperature configuration that you'll want explicit and visible in the demo/judging code review. Use the `BedrockModel(...)` object.

### 5. FastAPI + Pydantic patterns for the three endpoints

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI()

class CapturePayload(BaseModel):
    title: str
    description: str
    budget: float | None = None
    client_stats: dict | None = None
    raw_text: str

class EngagementRecord(BaseModel):
    engagement_id: str
    job: dict
    triage: dict | None = None
    proposal: dict | None = None
    contract: dict | None = None
    ops: dict | None = None

@app.post("/capture", response_model=EngagementRecord)
async def capture(payload: CapturePayload):
    engagement_id = str(uuid4())
    # persist skeleton record, kick off supervisor -> gig_triage_agent
    ...
    return record

@app.get("/engagements/{engagement_id}", response_model=EngagementRecord)
async def get_engagement(engagement_id: str):
    record = load_record(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return record

class AdvanceRequest(BaseModel):
    stage: str  # "triage" | "proposal" | "ops"

@app.post("/engagements/{engagement_id}/advance", response_model=EngagementRecord)
async def advance(engagement_id: str, req: AdvanceRequest):
    record = load_record(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    # dispatch to supervisor for the requested stage, mutate + persist record
    ...
    return record
```
This is a standard, well-established FastAPI pattern (Pydantic `BaseModel` for both request bodies and `response_model`, path params typed as `str`/`uuid`, `HTTPException` for 404s) — nothing exotic needed. Keep the Engagement Record read/write behind a small `load_record`/`save_record` pair (JSON file or SQLite row) so agent code never touches I/O directly.

### 6. Chrome MV3 extension → localhost FastAPI: CORS and permissions

**manifest.json** (service worker performs the fetch, per PROJECT.md's own stated design — this is the correct MV3 pattern):
```json
{
  "manifest_version": 3,
  "name": "Freelance Autopilot Capture",
  "version": "1.0",
  "permissions": ["activeTab", "storage"],
  "host_permissions": ["http://localhost:8000/*"],
  "background": { "service_worker": "background.js" },
  "action": { "default_popup": "popup.html" }
}
```
- `host_permissions` (not `permissions`) is where MV3 puts cross-origin URL match patterns; declaring `http://localhost:8000/*` here grants the **extension's background service worker** unrestricted cross-origin `fetch`/`XMLHttpRequest` to that origin — this is a Chrome-extension-specific privilege that a normal webpage does not get, and it is why PROJECT.md is correct to route the fetch through `background.js` rather than `popup.js`/content scripts (content-script-initiated fetches are still subject to the page's CORS rules; service-worker-initiated fetches under a granted host permission are not).
- Because of that host-permission bypass, strict FastAPI CORS middleware is **not required** for the extension call to succeed. Add it anyway for two reasons: (a) defense/clarity if you ever also open `popup.html` directly in a browser tab for debugging, and (b) most browsers/some Chrome versions still send a preflight `OPTIONS` for non-simple requests (JSON body + custom headers), and FastAPI's `CORSMiddleware` is what answers that preflight correctly:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "chrome-extension://<your-extension-id>"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```
The extension ID is only known after "Load unpacked" (or after publishing) — get it from `chrome://extensions` in developer mode and hardcode it into the FastAPI CORS list for the demo; there is no wildcard-safe way to allow "any chrome-extension origin" and you don't need one for a single-demo local API key setup.
- **What NOT to use:** don't request `<all_urls>` in `host_permissions` "to be safe" — it triggers Chrome's broader permission warning and isn't needed for a single localhost target; scope it to `http://localhost:8000/*` (or whatever port `uvicorn` binds).

### 7. AgentCore stretch — session/memory API (LOW CONFIDENCE, flag before building)

- The relevant integration lives in a **separate package**, `bedrock-agentcore` (install extra: `pip install 'bedrock-agentcore[strands-agents]'`), not in `strands-agents` itself.
- Verified imports/classes:
```python
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
```
- Minimal wiring:
```python
config = AgentCoreMemoryConfig(memory_id="...", session_id="...", actor_id="...")
with AgentCoreMemorySessionManager(config, region_name="us-east-1") as session_manager:
    agent = Agent(session_manager=session_manager)
```
- **Flag explicitly:** Strands' own documentation states this AgentCore Memory session-manager integration is **"community-maintained... not owned or supported by the Strands team"** and recommends validating it before production use. Combined with PROJECT.md already scoping AgentCore as "cut first if the timeline slips," this is a strong signal to treat AgentCore Memory as genuinely optional/experimental, not a load-bearing dependency — build the file/SQLite Engagement Record path first and fully working, and only bolt on AgentCore Memory afterward, isolated behind a swappable persistence interface, so cutting it late costs nothing. Do not commit to AgentCore Memory as the *only* persistence path.
- Not independently verified in this research pass: AgentCore Runtime deployment mechanics (how a Strands agent gets packaged/deployed as an AgentCore Runtime agent) — PROJECT.md mentions this but it's out of scope for this STACK research pass focused on the SDK/library surface; research this specifically before attempting the stretch deployment.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Agents-as-Tools for supervisor/specialists | `strands.multiagent.Graph` (`GraphBuilder`) | If a later requirement needs explicit branching/parallel fan-out between specialists (e.g., proposal and a parallel risk-check running simultaneously) — Graph gives you explicit edges and parallel node execution that Agents-as-Tools doesn't |
| Agents-as-Tools | `strands.multiagent.Swarm` | If the project pivots to open-ended, non-demo use where specialists should dynamically decide to loop back to each other (e.g., Ops Agent calling back into Proposal-Contract Agent mid-negotiation) — wrong for a judged, deterministic demo |
| File/SQLite Engagement Record | AgentCore Memory (`AgentCoreMemorySessionManager`) | Only if the AgentCore stretch goal is actively being pursued and there's schedule slack to validate a community-maintained integration; otherwise stick with file/SQLite per PROJECT.md's own stated fallback |
| Bare `strands-agents` install | `bedrock-agentcore-starter-toolkit` / AgentCore CLI scaffolding | Only needed once actually deploying to AgentCore Runtime, not for local FastAPI-hosted development |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pre-1.0 Strands docs (`strandsagents.com/0.1.x/...`) or any pre-1.0 code samples found via search | API has moved since 0.1.x (e.g., `strands.models.bedrock` import path, `Agent` constructor args have changed); following stale examples wastes hackathon time on broken imports | Only the current `/docs/...` (non-versioned) path on strandsagents.com, or the `sdk-python` GitHub repo's current `main` branch |
| `strands.multiagent.Swarm` as the supervisor mechanism | Model-driven handoff is non-deterministic run-to-run — directly conflicts with "runs deterministically for a ≤5-minute demo" requirement | Agents-as-Tools (see §2) |
| Manual string-matching / keyword routing instead of Strands tool-calling to pick a specialist | Duplicates what the SDK's function-calling loop already does; also isn't "genuine Strands multi-agent orchestration visible in the code" for judging | Wrap each specialist in `@tool` and let the supervisor's model pick via normal tool-calling |
| Bare `anthropic.claude-3-5-sonnet-20241022-v2:0` foundation-model ID for On-Demand throughput in most regions | Many Claude models on Bedrock require an inference-profile ID (`us.` / `global.` prefixed) rather than the bare FM ID for on-demand invocation in most regions — using the bare ID commonly throws a Bedrock `ValidationException` | Use the region-appropriate inference profile ID (e.g., `us.anthropic.claude-sonnet-4-6`), confirmed against your AWS account's Bedrock model access page |
| `<all_urls>` in the extension's `host_permissions` | Broader Chrome permission warning than needed; no benefit for a single localhost target | Scope to the exact `http://localhost:<port>/*` pattern |
| `allow_origins=["*"]` with `allow_credentials=True` in FastAPI CORS | Browsers reject wildcard origin + credentials combination outright; silently breaks the extension's fetch if you ever add cookies/auth headers | Explicit origin list including the `chrome-extension://<id>` origin |
| Treating AgentCore Memory as a required dependency for the MVP | It's a community-maintained integration per Strands' own docs, and PROJECT.md already marks AgentCore as first-to-cut | Build on file/SQLite persistence first; layer AgentCore Memory in only if time allows, behind a swappable interface |

## Stack Patterns by Variant

**If pursuing the AgentCore stretch goal:**
- Use `bedrock-agentcore[strands-agents]`'s `AgentCoreMemorySessionManager` for the supervisor's session state, but keep the Engagement Record's authoritative JSON shape identical to the file/SQLite version so switching is a config change, not a schema rewrite.
- Because the integration is community-maintained, budget explicit verification time (a smoke test against a real AgentCore Memory resource) before relying on it in the demo recording — a live-demo failure here is worse than not attempting it.

**If time runs short (base case per PROJECT.md's own risk framing):**
- Skip AgentCore entirely; ship file-based (or SQLite) Engagement Records and a supervisor running Agents-as-Tools purely within the FastAPI process. This is the fully-supported, zero-extra-dependency path and satisfies every "Active" requirement in PROJECT.md without the stretch.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `strands-agents` ≥1.0 | Python 3.10+ | Older Python versions unsupported per current quickstart docs |
| `strands-agents` `BedrockModel` | `boto3` (any recent version pulled transitively) | Region resolution falls back to `us-west-2` if nothing else is set — set `region_name` explicitly to avoid surprise cross-region latency/model-availability mismatches |
| `bedrock-agentcore[strands-agents]` | `strands-agents` ≥1.0 | Verify the two are pinned together at install time; as a community integration it may lag behind Strands' latest minor releases |
| FastAPI (≥0.100) | Pydantic v2 | Default in modern FastAPI; don't mix Pydantic v1 model definitions in with the Strands `structured_output()` calls, which expect standard Pydantic `BaseModel` v2 semantics |

## Sources

- https://strandsagents.com/docs/user-guide/quickstart/python/ — install command, minimal `Agent`, `@tool` decorator basics, Python 3.10+ requirement (fetched directly, HIGH confidence)
- https://pypi.org/project/strands-agents/ — current version 1.54.0, released 2026-08-27 (fetched directly, HIGH confidence)
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/multi-agent-patterns/ — overview of Graph/Swarm/Workflow/Agents-as-Tools shapes (fetched directly; page itself was conceptual with limited code, MEDIUM confidence on exact Graph import — recommend re-verifying `GraphBuilder` signature at build time)
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/ — verified `@tool`-wrapped specialist agent pattern and supervisor construction code (fetched directly, HIGH confidence)
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/swarm/ — verified `from strands.multiagent import Swarm` import and constructor shape (fetched directly, HIGH confidence)
- https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/ — `BedrockModel` import, model IDs, region/credential resolution order, full `Agent(model=...)` example (fetched directly, HIGH confidence)
- Search results referencing `strandsagents.com/docs/api/python/strands.tools.decorator/` and `strands.types.tools` — `@tool` return-value auto-wrapping into `ToolResult`, `structured_output()` method and Pydantic-as-tool-schema mechanism (via search summary, not direct fetch — MEDIUM confidence, matches expected pattern from other tool-calling SDKs)
- https://strandsagents.com/docs/integrations/session-managers/agentcore-memory/ — `AgentCoreMemoryConfig`/`AgentCoreMemorySessionManager` imports and code, explicit "community-maintained, not supported by the Strands team" caveat (fetched directly, HIGH confidence on the caveat itself; LOW confidence this reflects the absolute latest state given the disclaimer)
- FastAPI CORS: general web search consensus (`fastapi.tiangolo.com/tutorial/cors/` referenced) plus standard FastAPI/Starlette `CORSMiddleware` knowledge — not independently fetched in full; MEDIUM confidence, but this is stable, long-standing FastAPI API surface unlikely to have changed
- Chrome MV3 `host_permissions` / service-worker CORS-bypass behavior: general web search consensus (`developer.chrome.com/docs/extensions/develop/concepts/network-requests`, MDN) — not independently fetched in full; MEDIUM-HIGH confidence, this is well-documented, stable Chrome extension platform behavior

---
*Stack research for: Freelance Autopilot (Strands Agents SDK multi-agent backend, FastAPI, Bedrock/Claude, MV3 extension)*
*Researched: 2026-09-01*
