# Architecture Research

**Domain:** Multi-agent orchestration system (Strands Agents SDK) fronted by a REST API and a browser extension capture point
**Researched:** 2026-09-01
**Confidence:** HIGH (Strands multi-agent pattern verified against official docs at strandsagents.com; AgentCore memory verified against official AWS/Strands integration docs)

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│  CAPTURE LAYER                                                         │
│  Chrome Extension (Manifest V3)                                       │
│  ┌───────────┐   paste job text/URL   ┌───────────────────────────┐   │
│  │ popup.html│ ───────────────────────▶│ background.js (service    │   │
│  │ popup.js  │                         │ worker — owns fetch, CORS)│   │
│  └───────────┘◀─────────────────────── └──────────────┬────────────┘   │
│    renders verdict/score/reasoning inline               │ HTTPS POST   │
└──────────────────────────────────────────────────────────┼────────────┘
                                                             ▼
┌───────────────────────────────────────────────────────────────────────┐
│  API LAYER — FastAPI (backend/api.py)                                 │
│  POST /capture                 GET /engagements/{id}                  │
│  POST /engagements/{id}/advance                                       │
│  Owns: request validation, Engagement Record load/save, calling the   │
│  Supervisor synchronously, returning the updated record slice.        │
└───────────────────────────────────────┬─────────────────────────────┘
                                          │ invokes with a plain-text or
                                          │ structured task + relevant
                                          │ Engagement Record slice
                                          ▼
┌───────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER — Supervisor Agent (Strands `Agent`)             │
│  system_prompt: routing logic ("if stage==triage, call gig_triage...")│
│  tools = [gig_triage_agent.as_tool(...),                              │
│           proposal_contract_agent.as_tool(...),                       │
│           ops_agent.as_tool(...)]      (agents-as-tools pattern)      │
│                                                                        │
│   ┌─────────────────┐  ┌───────────────────────┐  ┌────────────────┐ │
│   │ Gig Triage Agent │  │ Proposal-Contract      │  │ Ops Agent      │ │
│   │ (Strands Agent)  │  │ Agent (Strands Agent)  │  │ (Strands Agent)│ │
│   │ tools:           │  │ tools:                 │  │ tools:         │ │
│   │ extract_job_     │  │ draft_proposal         │  │ check_scope_   │ │
│   │  fields          │  │ draft_contract         │  │  creep         │ │
│   │ kill_switch_     │  │ check_scope_clarity    │  │ check_invoice_ │ │
│   │  check (det.)    │  │                        │  │  status        │ │
│   │ llm_scorecard    │  │ escalates: needs_human_│  │ draft_status_  │ │
│   │ (no escalation)  │  │  input + question      │  │  update        │ │
│   └────────┬─────────┘  └──────────┬─────────────┘  └───────┬────────┘ │
│            │ returns structured    │ returns structured     │ returns  │
│            │ dict (verdict/score/  │ dict (proposal/contract/│ list of  │
│            │ reasoning)            │ needs_human_input)      │ flags    │
└────────────┼───────────────────────┼─────────────────────────┼─────────┘
             ▼                       ▼                         ▼
┌───────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE LAYER — Engagement Record store                          │
│  demo: JSON file per engagement (data/engagements/{id}.json)          │
│  optional: SQLite table {id, json_blob, updated_at}                   │
│  stretch: AgentCore Memory (session_id=engagement_id) for cross-turn  │
│  continuity if deployed to AgentCore Runtime                          │
└───────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Chrome Extension (popup + background) | Paste-based capture UI; renders triage result inline; never talks to the LLM directly | Vanilla JS, Manifest V3, `background.js` service worker performs `fetch()` to sidestep popup CORS/context restrictions |
| FastAPI backend | Single source of truth for HTTP contract; loads/saves the Engagement Record; the *only* caller of the Supervisor Agent | `api.py` with `/capture`, `/engagements/{id}`, `/engagements/{id}/advance`; Pydantic models mirroring the Engagement Record shape |
| Supervisor Agent | Routes a stage-scoped task to exactly one specialist per call; does NOT re-implement specialist logic; assembles/normalizes specialist output before handing back to FastAPI | Strands `Agent` with the three specialists wired in via `.as_tool()` (agents-as-tools pattern — verified as Strands' documented supervisor/orchestrator pattern) |
| Gig Triage Agent | Deterministic gate + LLM scoring; fully autonomous, no escalation path by design | Strands `Agent` with `@tool` functions: `extract_job_fields`, `kill_switch_check` (pure Python, no LLM), `llm_scorecard` |
| Proposal-Contract Agent | Drafts proposal/contract/payment schedule; the one stage with an explicit escalation output field | Strands `Agent` with `@tool` functions: `draft_proposal`, `draft_contract`, `check_scope_clarity` |
| Ops Agent | Runs against fixture client thread + payment schedule; emits one escalation "card" per flag type | Strands `Agent` with `@tool` functions: `check_scope_creep`, `check_invoice_status`, `draft_status_update` |
| Engagement Record store | Single JSON document per engagement; read-modify-write per stage transition | File-based JSON for the demo (simplest, zero setup, human-inspectable for the video); SQLite only if concurrent-access safety is needed |

## Recommended Project Structure

```
backend/
├── api.py                      # FastAPI app: /capture, /engagements/{id}, /engagements/{id}/advance
├── agents/
│   ├── supervisor.py            # Supervisor Agent def + routing system prompt + .as_tool() wiring
│   ├── gig_triage_agent.py      # Agent + system prompt + tool imports
│   ├── proposal_contract_agent.py
│   └── ops_agent.py
├── tools/
│   ├── extract_job_fields.py
│   ├── kill_switch_check.py     # pure Python, deterministic — no LLM call
│   ├── llm_scorecard.py
│   ├── draft_proposal.py
│   ├── draft_contract.py
│   ├── check_scope_clarity.py
│   ├── check_scope_creep.py
│   ├── check_invoice_status.py
│   └── draft_status_update.py
├── models/
│   └── engagement_record.py     # Pydantic model = the shared-state schema (single source of truth)
├── store/
│   └── engagement_store.py      # load(id) / save(id, record) — file-based; swap-in point for SQLite/AgentCore later
├── fixtures/
│   ├── sample_upwork_jobs.json
│   ├── sample_client_thread.json
│   └── sample_payment_schedule.json
├── data/engagements/             # runtime JSON files (gitignored, seeded fresh per demo run)
└── requirements.txt

extension/
├── manifest.json
├── popup.html / popup.js
├── background.js                 # fetch() to backend, avoids popup CORS
└── styles.css
```

### Structure Rationale

- **`agents/` vs `tools/` split:** Strands' own convention is agent = system prompt + tool list; tools are plain `@tool`-decorated functions. Keeping them in separate modules makes it visually obvious in the code (and to judges) that each specialist is a real orchestrated `Agent`, not an inline prompt string — this directly serves the judging criterion "genuine multi-agent orchestration visible in the code."
- **`models/engagement_record.py` as the one schema:** every agent tool that mutates the record should accept/return a typed slice of this model (or a dict validated against it) rather than free-form text, so the Supervisor's job of merging specialist output back into the record is a typed field assignment, not string parsing.
- **`store/engagement_store.py` as an interface, not a concrete backend:** isolates the file-vs-SQLite decision so it can change without touching agent or API code, and is the seam where an AgentCore session/memory backend would slot in for the stretch goal.

## Architectural Patterns

### Pattern 1: Agents-as-Tools (Supervisor/Orchestrator pattern)

**What:** The Supervisor is a Strands `Agent` whose `tools` list contains the three specialist agents, each wrapped with `.as_tool(name=..., description=...)`. Calling the Supervisor causes its underlying LLM to pick which specialist tool to invoke based on the task and the specialist's `description`. This is Strands' own documented name for exactly this shape ("orchestrator and specialists" / "agents as tools").
**When to use:** When each specialist has a distinct, non-overlapping responsibility and the routing decision itself needs judgment (or, as here, is deterministic per demo stage and can be forced). Verified as the officially supported multi-agent pattern for hierarchical delegation in Strands (alternatives are `Graph` and `Swarm`, which are for peer-to-peer/parallel patterns and are not the right fit here since the PRD's flow is a strict, mostly-linear stage sequence).
**Trade-offs:** Simple, debuggable, and matches the PRD's "supervisor + 3 specialists" framing exactly. Downside: default `.as_tool()` behavior returns specialist output as a plain string, which the Supervisor's own LLM would then re-summarize — undesirable when the specialist's output is a structured dict the API needs verbatim. Mitigation below.

**Example:**
```python
from strands import Agent

triage_tool = gig_triage_agent.as_tool(
    name="gig_triage_agent",
    description="Extract job fields, run the kill-switch gate, and score fit. "
                 "Call this when stage == 'triage'.",
)
proposal_tool = proposal_contract_agent.as_tool(
    name="proposal_contract_agent",
    description="Draft proposal, contract, and payment schedule. "
                 "Call this when stage == 'proposal' and triage verdict == 'apply'.",
)
ops_tool = ops_agent.as_tool(
    name="ops_agent",
    description="Check scope creep, invoice status, and draft a status update. "
                 "Call this when stage == 'ops'.",
)

supervisor = Agent(
    system_prompt=(
        "You route a single engagement-stage task to exactly one specialist tool "
        "based on the `stage` field in the input. Never answer the task yourself."
    ),
    tools=[triage_tool, proposal_tool, ops_tool],
)
```

### Pattern 2: Structured tool contract instead of free-text delegation

**What:** Rather than relying on the Supervisor's LLM to synthesize/paraphrase a specialist's answer (the default `.as_tool()` text-in/text-out contract), each specialist's underlying `@tool` functions return **typed dicts/Pydantic models** matching the Engagement Record's per-stage schema (e.g. `{verdict, score, reasoning, extracted_fields}`), and the specialist `Agent`'s own system prompt instructs it to emit exactly that JSON shape as its final response (Strands supports structured output via response format / tool-return typing). FastAPI parses that JSON directly into the Engagement Record slice — the Supervisor's LLM round-trip is for *routing*, not for *reshaping data*.
**When to use:** Always, for this project — the demo's determinism requirement (5-minute video, no manual glue) means agent output must land in the Engagement Record without lossy re-summarization.
**Trade-offs:** Slightly more prompt-engineering work per specialist (must reliably emit valid JSON) but removes a whole class of "the supervisor paraphrased the verdict" bugs. `delegate=True` (Strands' pass-through mode noted in docs) is the closer built-in fit if the API version supports it: it skips the extra orchestrator model round-trip and returns the specialist's raw response untouched — verify support before implementation and prefer it over manual re-parsing.

**Example:**
```python
# In FastAPI /engagements/{id}/advance:
record = store.load(engagement_id)
task = {"stage": record.next_stage, "engagement": record.model_dump()}
raw = supervisor(str(task))          # or supervisor(task, delegate expectation)
specialist_output = json.loads(extract_json(str(raw)))
record.apply_stage_output(record.next_stage, specialist_output)  # typed merge
store.save(engagement_id, record)
```

### Pattern 3: Engagement Record as the sole shared-state channel (not Strands session state)

**What:** Strands does provide in-process mechanisms for shared state — `Agent.state` (out-of-band key/value state per agent instance) and `invocation_state` (kwargs threaded through Graph/Swarm patterns and exposed to `@tool(context=True)` functions) — but both are scoped to a single Python process/agent lifetime. Because the FastAPI backend here is called per-HTTP-request from an extension and each `/advance` call is stage-by-stage (with a real time-jump between proposal and ops), the durable shared-state channel must be the persisted Engagement Record file/row, not Strands' in-memory state. Strands' own `Agent.state`/`invocation_state` should be used only for *within-a-single-call* bookkeeping (e.g. passing today's fixture set to a tool without polluting the prompt), never as the system of record.
**When to use:** Any multi-stage agent system where stages are invoked from separate HTTP requests / separate process lifetimes (true here since the demo has an explicit "time-jump" between Stage 2 and Stage 3).
**Trade-offs:** Requires an explicit read-modify-write around every Supervisor call (a few extra lines in `api.py`) but makes the system trivially resumable, inspectable (the JSON file *is* the demo's evidence trail), and decoupled from any one Strands SDK version's session-management API.

## Data Flow

### Request Flow (per PRD §6.1, 6-step flow)

```
1. CAPTURE
   Extension popup (paste job text/URL)
     → background.js fetch → POST /capture {raw_text, url?}
     → FastAPI: creates Engagement Record {engagement_id: uuid, job: {}, triage: null, ...}
     → calls Supervisor(stage="triage") → Gig Triage Agent
         → extract_job_fields (LLM) → kill_switch_check (deterministic) → llm_scorecard (LLM)
         → returns {verdict, score, reasoning, extracted_fields}
     → FastAPI merges into record.triage, record.job; store.save()
     → response to extension: {engagement_id, verdict, score, reasoning}
   Extension renders verdict/score/reasoning inline.  ◀── end Stage 1

2. TRIAGE VERDICT GATE
   If verdict == "skip": engagement ends here (record stays, no further advance).
   If verdict == "apply": user (or demo auto-flow) calls
     → POST /engagements/{id}/advance {target_stage: "proposal"}

3. PROPOSAL / CONTRACT
     → FastAPI loads record → calls Supervisor(stage="proposal", engagement=record)
     → Proposal-Contract Agent: check_scope_clarity → draft_proposal → draft_contract
         → if scope/budget ambiguous: returns {needs_human_input: true, question: "..."}
           ⚑ HUMAN-IN-THE-LOOP POINT #1 — FastAPI surfaces `question` in the /advance
             response; record.proposal.needs_human_input stays true until a follow-up
             /advance call carries a human-supplied answer merged into the task input.
         → else: returns {proposal, contract, payment_schedule, needs_human_input: false}
     → FastAPI merges into record.proposal, record.contract; store.save()

4. TIME-JUMP FIXTURE LOAD
     → POST /engagements/{id}/advance {target_stage: "ops", load_fixtures: true}
     → FastAPI reads fixtures/sample_client_thread.json + sample_payment_schedule.json
       and attaches them to the task payload (NOT persisted into the permanent record
       until Ops Agent has run — fixtures are simulation input, record.ops is real output)

5. OPS
     → Supervisor(stage="ops", engagement=record, client_thread=..., payment_schedule=...)
     → Ops Agent: check_scope_creep, check_invoice_status, draft_status_update
         → each positive check appends a distinct entry to record.ops.scope_creep_flags /
           record.ops.invoice_flags — these ARE the escalation cards
           ⚑ HUMAN-IN-THE-LOOP POINTS #2 (scope creep) and #3 (overdue invoice) —
             structural because they only fire when the deterministic/LLM check finds
             a real mismatch against the signed SOW or schedule, not on every run
     → FastAPI merges into record.ops; store.save()

6. RENDER
     → GET /engagements/{id} returns the full record; a minimal demo UI (or the
       video's screen recording of raw JSON / a thin HTML view) shows the accumulated
       triage → proposal → ops trail as one artifact.
```

### State Management

```
Engagement Record (single JSON document, keyed by engagement_id)
    ↓ read                                    ↑ write (typed merge, one stage at a time)
FastAPI endpoint handler
    ↓ constructs stage-scoped task             ↑ receives structured specialist output
Supervisor Agent (routes only)
    ↓ delegates via .as_tool()                 ↑ specialist's typed JSON response
Gig Triage / Proposal-Contract / Ops Agent (owns its slice's business logic + tools)
```

No agent ever writes directly to the store. FastAPI is the only writer, which keeps the persistence boundary a single, testable seam and avoids concurrent-write races between specialists.

### Key Data Flows

1. **Stage advance flow:** every `/advance` call is one full read-modify-write cycle: load record → build task from record + (fixtures, if stage requires) → Supervisor routes to one specialist → specialist tools run → specialist returns typed output → FastAPI merges into the correct record slice → save → return the slice (or the whole record) to the caller. This is the same shape for all three stages; only the task payload and the merged slice differ.
2. **Escalation flow:** an escalation is not a separate channel — it is a boolean/field on the specialist's normal structured output (`needs_human_input` + `question` for Proposal-Contract; a non-empty `scope_creep_flags`/`invoice_flags` list for Ops). FastAPI's job is simply to surface those fields distinctly in the API response (e.g. a `escalations: []` array in the `/advance` response) so the extension/demo UI can render them as cards without any extra polling mechanism.

## Scaling Considerations

Not relevant at production scale for a hackathon demo — noted briefly for completeness.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Demo (1 user, ≤10 engagements) | File-based JSON is fine; no concurrency concerns; everything in this doc as-is |
| Small real usage (1 user, 100s of engagements) | Move Engagement Record to SQLite (one row per engagement, JSON column) purely for query convenience (list/filter), not for concurrency |
| Multi-user / stretch AgentCore deployment | AgentCore Memory session per engagement (`session_id = engagement_id`, `actor_id = user_id`); Supervisor + specialists deployed as AgentCore Runtime agents; this is where the PRD's stretch goal lives |

### Scaling Priorities

1. **First real constraint:** demo determinism, not scale — fixtures must be static and idempotent so re-running `/advance` for Stage 3 always produces the same scope-creep/invoice flags in the recorded video.
2. **Second:** if the AgentCore stretch is attempted, the risk is API drift (Strands + AgentCore integration is actively evolving) — isolate it behind the `store/engagement_store.py` interface and a feature flag so the file-based path keeps working as the fallback demo path right up to the deadline.

## Anti-Patterns

### Anti-Pattern 1: Single wrapped LLM call disguised as "multi-agent"

**What people do:** Build one big Strands `Agent` with a giant system prompt and all nine tools attached directly, skipping the Supervisor and the three specialist `Agent` objects entirely.
**Why it's wrong:** This is explicitly called out in the PRD/PROJECT.md as the failure mode judges are watching for ("genuine multi-agent Strands orchestration... not a single wrapped LLM call"). It also collapses the escalation semantics — there's no clean place to say "only the Proposal-Contract Agent's output has a `needs_human_input` field."
**Do this instead:** Keep the Supervisor as a distinct `Agent` whose only tools are the three specialist `Agent`s (via `.as_tool()`), and keep each specialist as its own `Agent` with its own system prompt and only its own tools. The hierarchy must be visible both in the code and in the architecture diagram.

### Anti-Pattern 2: Letting the Supervisor's LLM re-author specialist output

**What people do:** Rely on the default `.as_tool()` text-in/text-out contract and let the Supervisor's model paraphrase or summarize what the specialist said before it reaches the API layer.
**Why it's wrong:** Breaks determinism (the same specialist output can get reworded differently across two demo runs) and risks losing structured fields (`needs_human_input`, `score`, flag lists) inside prose.
**Do this instead:** Have specialists return strict JSON matching the Engagement Record schema; parse that JSON directly in FastAPI. Use `delegate=True` / raw pass-through if the installed Strands version supports it for this exact purpose; otherwise instruct the Supervisor's system prompt to return the specialist's JSON verbatim with no added commentary, and validate that assumption early with a smoke test before building the rest of the system on top of it.

### Anti-Pattern 3: Treating Strands `Agent.state` / AgentCore Memory as the system of record

**What people do:** Assume the SDK's built-in state or memory API will "just persist" the Engagement Record across the extension → API → time-jump → ops flow.
**Why it's wrong:** `Agent.state`/`invocation_state` are scoped to a single agent instance's process lifetime (verified via Strands docs), and AgentCore Memory is a stretch-goal-only integration with an evolving API surface not needed for the core demo. Building the file-based demo path on top of either dependency risks breaking core functionality if that API changes or if AgentCore setup slips.
**Do this instead:** Persist the Engagement Record independently (file/SQLite) as designed above; treat AgentCore Memory purely as an optional, additively-wired persistence backend behind the same `engagement_store` interface, wired in only after the core file-based path is fully working end to end.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Claude via Amazon Bedrock | Strands `Agent(model=...)` bedrock model provider | Standard Strands Bedrock model integration; verify current Bedrock model ID string against Strands docs at implementation time (model IDs/regions drift) |
| Amazon Bedrock AgentCore (stretch) | AgentCore Runtime hosts Supervisor + specialists as deployed agents; `AgentCoreMemorySessionManager` (`memory_id`, `session_id`, `actor_id`) for session persistence | Cut first if timeline slips per PROJECT.md; verified integration exists (`strandsagents.com/docs/integrations/session-managers/agentcore-memory/`) but adds real infra setup (create Memory resource, IAM, deploy) |
| Chrome Extension APIs | `chrome.runtime` messaging between popup and background service worker; `fetch()` from `background.js` to the FastAPI backend | Manifest V3 requires the service-worker-owns-fetch pattern noted in PROJECT.md to avoid popup-context CORS/lifecycle issues |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Extension ↔ FastAPI | HTTPS JSON (`POST /capture`) | Single local API key in a header for the demo; no user auth system needed |
| FastAPI ↔ Supervisor | Direct in-process Python call (`supervisor(task)`) | Not a network hop — Supervisor runs inside the same FastAPI process/worker |
| Supervisor ↔ Specialists | Strands `.as_tool()` call (in-process, LLM-mediated routing) | This is the boundary that must show up unambiguously as "multi-agent" in code and diagram |
| FastAPI ↔ Engagement Record store | `store.load(id)` / `store.save(id, record)` | Only FastAPI writes; specialists/Supervisor never touch the store directly — keeps a single, auditable write path |
| Fixtures ↔ Ops Agent | Loaded by FastAPI and passed into the Supervisor's task payload for the ops stage only | Fixtures are simulation input, not part of the persisted record's history until Ops Agent output is merged back |

## Suggested Build Order

Dependency-ordered; each step should be independently runnable/testable before the next begins.

1. **Engagement Record model + file-based store** (`models/engagement_record.py`, `store/engagement_store.py`). Everything else reads/writes this shape — build and unit-test it first, including the `apply_stage_output()` merge logic, before any agent exists.
2. **Gig Triage Agent + its tools, standalone** (no Supervisor, no API yet). Call it directly from a script against a couple of fixture job postings; validate `kill_switch_check` (pure Python, test without any LLM) and `llm_scorecard` output shape.
3. **Supervisor Agent wrapping just the Gig Triage Agent** via `.as_tool()`. Prove the agents-as-tools routing pattern end-to-end on the smallest possible slice before adding the other two specialists — this is the highest-risk/most novel piece (verify against live Strands version) and should be de-risked early.
4. **FastAPI `/capture` endpoint** wired to the Supervisor from step 3 + the store from step 1. This gives a demoable Stage 1 (capture → triage) before touching the extension.
5. **Chrome extension (capture UI only)** against the working `/capture` endpoint. Extension work is independent of Stages 2–3 and can proceed in parallel with step 6 once `/capture` is stable.
6. **Proposal-Contract Agent + tools**, added as a second Supervisor tool; `/engagements/{id}/advance` endpoint (stage="proposal") added to FastAPI. Test the escalation path (`needs_human_input`) explicitly with a deliberately ambiguous fixture job.
7. **Fixtures for Stage 3** (`sample_client_thread.json`, `sample_payment_schedule.json`) authored with a deliberate scope-creep message and one overdue milestone baked in, so Ops Agent behavior is deterministic from the start.
8. **Ops Agent + tools**, added as the third Supervisor tool; extend `/advance` to accept stage="ops" and to load/attach the Stage 3 fixtures. Test that both escalation cards (scope creep, overdue invoice) fire against the fixtures from step 7.
9. **Full demo run-through** (extension capture → triage → advance to proposal → advance to ops) recorded once for timing, before polishing README/diagram/demo script.
10. **(Stretch, cut first if behind schedule) AgentCore deployment**: swap the store's backend behind the existing `engagement_store` interface to `AgentCoreMemorySessionManager`, deploy Supervisor + specialists to AgentCore Runtime. Only attempt after step 9's file-based demo is fully working and recorded as a fallback.

This order front-loads the two highest-uncertainty items — the Engagement Record schema (everything downstream depends on it) and the Strands agents-as-tools routing mechanism (the core judged criterion) — before any UI or fixture polish work, and keeps the AgentCore stretch fully decoupled so cutting it late costs nothing already built.

## Sources

- [Agents as Tools — Strands Agents SDK official docs](https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/)
- [Multi-agent Patterns — Strands Agents SDK official docs](https://strandsagents.com/docs/user-guide/concepts/multi-agent/multi-agent-patterns/)
- [State Management — Strands Agents SDK official docs](https://strandsagents.com/docs/user-guide/concepts/agents/state/)
- [AgentCore Memory Session Manager — Strands Agents SDK official docs](https://strandsagents.com/docs/integrations/session-managers/agentcore-memory/)
- [Strands Agents SDK - Amazon Bedrock AgentCore devguide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/strands-sdk-memory.html)
- [Multi-Agent collaboration patterns with Strands Agents and Amazon Nova — AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/)
- [Strands Agents SDK: A technical deep dive into agent architectures and observability — AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/)
- Project source docs: `/home/user/Freelance-Autopilot/.planning/PROJECT.md`, `/home/user/Freelance-Autopilot/docs/PRD.md`

---
*Architecture research for: Freelance Autopilot (Strands supervisor + 3-specialist multi-agent system)*
*Researched: 2026-09-01*
