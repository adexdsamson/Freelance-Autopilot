<!-- GSD:project-start source:PROJECT.md -->

## Project

**Freelance Autopilot**

Freelance Autopilot is an agentic system that owns the full lifecycle of a freelance
engagement end to end — from deciding whether a gig is worth applying to, through
drafting the proposal and contract, to running lightweight ops (status updates,
scope-creep detection, invoice tracking) once the engagement is live. It is built as a
supervisor agent orchestrating three specialist agents on the Strands Agents SDK, with a
Manifest V3 Chrome extension as the real-world capture point for Stage 1 and fixture data
driving Stages 2–3 for a controllable demo. It is a hackathon submission for the "Agents
for Humans" (AWS Strands Agents SDK) Professional Agents track and supersedes the
standalone "Gig Triage" (micro1) submission as its first stage.

**Core Value:** A freelancer captures a real job posting and the system runs it end to end through
genuine multi-agent Strands orchestration — triage verdict → proposal/contract draft →
live-engagement ops flags — with human-in-the-loop escalations that are structurally
justified, not decorative.

### Constraints

- **Timeline**: Hackathon deadline Sep 14, 2026 — roughly six weeks; tight for three agent stages + extension + optional AgentCore deploy + video.
- **Tech stack**: Strands Agents SDK, FastAPI, Claude via Bedrock, Manifest V3 vanilla JS.
- **Compliance**: No automated scraping of Upwork; paste-based capture only (ToS).
- **Demo**: Must run deterministically for a ≤5-minute recorded walkthrough; fixtures make Stages 2–3 repeatable.
- **Licensing**: Public repo with an MIT or Apache-2.0 license visible in the About section (submission rule).

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

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

# Core

# Bedrock model provider (bundled in strands-agents, no extra needed for Bedrock specifically

# — but boto3 must be present and AWS-credentialed)

# Optional prebuilt Strands tools

# Stretch: AgentCore Memory

# Dev/test

## Verified API Specifics (source of truth, not memory)

### 1. Strands Agents SDK — package, install, minimal Agent

- PyPI package: **`strands-agents`** (import name is `strands`, not `strands_agents` — classic PyPI-name/import-name split). Current version verified on PyPI: **1.54.0** (2026-08-27). Requires Python 3.10+.
- Minimal construction:
- Two calling conventions: natural-language (`agent("text")`) and direct tool invocation (`agent.tool.tool_name(param=...)`).
- Model defaults to Bedrock's Claude if `model` is omitted (Strands ships Bedrock as the default provider) — but for this project, pass an explicit `BedrockModel` (see §4) rather than relying on the default, so the model ID is visible and controlled in code.

### 2. Supervisor → specialist pattern — RECOMMENDATION: **Agents-as-Tools**

| Pattern | Import | Control flow | Fit for this project |
|---|---|---|---|
| **Agents-as-Tools** | `from strands import Agent, tool` (a specialist `Agent` is wrapped in an `@tool`-decorated function and passed into the supervisor's `tools=[...]`) | Supervisor's LLM decides which specialist tool to call, in normal tool-calling loop | **Recommended** |
| Graph | `from strands.multiagent import GraphBuilder` (not fully verified here — inferred from docs structure; verify signature before use) | Developer-defined directed graph, deterministic edges | Overkill: no branching/looping needed, three stages run in a fixed sequence already |
| Swarm | `from strands.multiagent import Swarm` | Agents autonomously hand off to each other; model-driven, non-deterministic entry/exit | Wrong fit: the PRD needs deterministic, judgeable escalation points, not free-form handoff |
| Workflow | Plain Python chaining of agent calls (code-level DAG, not an SDK primitive) | Fully developer-controlled | Viable fallback but forfeits the "genuine Strands multi-agent orchestration" visible in code that judges are scored on |

### 3. Defining tools — `@tool` decorator, typed results

- Import: `from strands import tool`.
- Decorate a plain Python function; the type hints and docstring become the tool's schema (name, description, args) presented to the model:
- Return handling: a plain string is auto-wrapped as `{"text": str(result)}`; a `dict` matching the `ToolResult` TypedDict shape (`{"status": "success"|"error", "content": [...], "toolUseId": ...}`) is used as-is; raised exceptions are converted to an error-status `ToolResult` automatically. For this project's tools (`extract_job_fields`, `llm_scorecard`, `check_scope_creep`, etc.) return a plain `dict` of your Engagement-Record-shaped fields — Strands' auto-wrapping handles the rest, no need to hand-construct `ToolResult` objects.
- For getting a **validated Pydantic object** back from an agent's final answer (as opposed to a tool call), use `agent.structured_output(YourPydanticModel, prompt)` — internally Strands registers your Pydantic model as a tool spec and validates the model's output against it. This is the right mechanism for forcing the Gig Triage Agent's final `{verdict, score, reasoning, extracted_fields}` into a strict schema you can drop directly into the Engagement Record. Recommend defining that response shape as a Pydantic `BaseModel` shared between the Strands call and the FastAPI response model.
- An agent calls a tool automatically as part of its normal loop once the tool is in its `tools=[...]` list — no separate registration step. Direct/manual invocation for testing: `agent.tool.tool_name(param=value)`.

### 4. Claude via Bedrock — model provider wiring

- Import: `from strands.models import BedrockModel`.
- Construction:
- Model ID: use a Bedrock **inference profile ID** (the `us.` or `global.` prefixed form), not the bare `anthropic.claude-...` foundation-model ID, for cross-region throughput — verify the exact current Claude model slug against your AWS account's enabled Bedrock models at build time (model IDs get versioned/renamed; don't hardcode from memory — confirm in the Bedrock console's "Model access" page before shipping).
- Credentials/region resolve through the standard boto3 chain: explicit `region_name` in `BedrockModel(...)` → boto3 session → `AWS_REGION` env var → default (`us-west-2`). For local dev, `aws configure` or exported `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` is enough; no Strands-specific credential mechanism exists.
- To pass a custom boto3 session (e.g., assumed role, non-default profile): `BedrockModel(model_id=..., boto_session=boto3.Session(...))`.
- **What NOT to use:** don't pass a raw model-id string directly to `Agent(model="...")` for production code even though it's supported — it hides region/credential/temperature configuration that you'll want explicit and visible in the demo/judging code review. Use the `BedrockModel(...)` object.

### 5. FastAPI + Pydantic patterns for the three endpoints

### 6. Chrome MV3 extension → localhost FastAPI: CORS and permissions

- `host_permissions` (not `permissions`) is where MV3 puts cross-origin URL match patterns; declaring `http://localhost:8000/*` here grants the **extension's background service worker** unrestricted cross-origin `fetch`/`XMLHttpRequest` to that origin — this is a Chrome-extension-specific privilege that a normal webpage does not get, and it is why PROJECT.md is correct to route the fetch through `background.js` rather than `popup.js`/content scripts (content-script-initiated fetches are still subject to the page's CORS rules; service-worker-initiated fetches under a granted host permission are not).
- Because of that host-permission bypass, strict FastAPI CORS middleware is **not required** for the extension call to succeed. Add it anyway for two reasons: (a) defense/clarity if you ever also open `popup.html` directly in a browser tab for debugging, and (b) most browsers/some Chrome versions still send a preflight `OPTIONS` for non-simple requests (JSON body + custom headers), and FastAPI's `CORSMiddleware` is what answers that preflight correctly:
- **What NOT to use:** don't request `<all_urls>` in `host_permissions` "to be safe" — it triggers Chrome's broader permission warning and isn't needed for a single localhost target; scope it to `http://localhost:8000/*` (or whatever port `uvicorn` binds).

### 7. AgentCore stretch — session/memory API (LOW CONFIDENCE, flag before building)

- The relevant integration lives in a **separate package**, `bedrock-agentcore` (install extra: `pip install 'bedrock-agentcore[strands-agents]'`), not in `strands-agents` itself.
- Verified imports/classes:
- Minimal wiring:
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

- Use `bedrock-agentcore[strands-agents]`'s `AgentCoreMemorySessionManager` for the supervisor's session state, but keep the Engagement Record's authoritative JSON shape identical to the file/SQLite version so switching is a config change, not a schema rewrite.
- Because the integration is community-maintained, budget explicit verification time (a smoke test against a real AgentCore Memory resource) before relying on it in the demo recording — a live-demo failure here is worse than not attempting it.
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

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
