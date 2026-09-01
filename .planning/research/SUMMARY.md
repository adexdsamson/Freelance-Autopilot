# Project Research Summary

**Project:** Freelance Autopilot
**Domain:** Multi-agent freelance engagement lifecycle automation (Strands Agents SDK supervisor/specialist backend + Bedrock/Claude + FastAPI + Manifest V3 Chrome extension)
**Researched:** 2026-09-01
**Confidence:** MEDIUM-HIGH

## Executive Summary

Freelance Autopilot is a hackathon submission (Strands Agents SDK "Agents for Humans" track, deadline Sep 14, 2026) that must demonstrate genuine multi-agent orchestration — not a single wrapped LLM call — across three sequential engagement stages: gig triage, proposal/contract drafting, and live-engagement ops. Experts building this kind of system on Strands use the **Agents-as-Tools** pattern: a Supervisor `Agent` whose `tools=[...]` list contains three specialist `Agent` instances (Gig Triage, Proposal-Contract, Ops), each with its own system prompt and tool set, wrapped via `.as_tool()`. This is the officially documented, verified Strands pattern for hierarchical delegation and is the right fit here because the PRD demands deterministic, judgeable staged control (via `/engagements/{id}/advance`) rather than model-driven, non-deterministic handoff (`Swarm`) or unneeded branching complexity (`Graph`).

The recommended approach: FastAPI hosts the Supervisor and specialists; a single Pydantic-modeled Engagement Record (JSON file or SQLite, never Strands' in-process `Agent.state`) is the durable shared-state channel read/written only by FastAPI, since stages are invoked from separate HTTP requests with a real time-jump between them. Each specialist's tools return typed dicts/Pydantic objects matching Engagement Record slices — never free-text the Supervisor re-paraphrases — to preserve determinism. Two structurally-repeated architecture patterns anchor the design: a deterministic gate cheaply rejecting/flagging before an LLM judgment call runs (Stage 1's kill-switch → scorecard; Stage 3's invoice-date-check vs. scope-creep judgment), and three structurally justified (not decorative) human-in-the-loop escalation points (scope/budget ambiguity, scope creep, overdue invoice) — deliberately absent at triage, which is fully autonomous.

The key risks are all about verification and discipline under time pressure, not novel technology: (1) guessing the Strands multi-agent API from stale training data instead of verifying against live docs, (2) accidentally building a "single wrapped LLM call" that looks multi-agent in the demo but fails judging on code inspection, (3) LLM nondeterminism breaking the required repeatable 5-minute demo unless verdict/escalation logic is pushed into deterministic Python, and (4) scope-creep on the AgentCore stretch goal consuming schedule that belongs to the three core agents. Mitigation is front-loading a Strands API verification spike, structurally separating specialist agents from day one, running fixtures 3x to confirm determinism before recording, and sequencing AgentCore strictly last with a hard time-box.

## Key Findings

### Recommended Stack

Core dependencies are `strands-agents` (≥1.0, current 1.54.0) for the agent/tool/orchestration framework, FastAPI + Pydantic v2 for the HTTP layer and shared schema definitions, and `boto3`-backed `BedrockModel` for Claude access via Amazon Bedrock. All are HIGH confidence, verified against official docs. AgentCore Memory (`bedrock-agentcore[strands-agents]`) is explicitly flagged LOW confidence — Strands' own docs call it "community-maintained... not owned or supported by the Strands team" — and should be treated as an optional, swappable stretch, never a load-bearing dependency.

**Core technologies:**
- `strands-agents` (`Agent`, `@tool`, `.as_tool()`, `BedrockModel`) — required orchestration framework; API stabilized post-1.0, pre-1.0 docs are stale and must be avoided
- FastAPI + Pydantic v2 — async HTTP backend hosting the supervisor; one shared schema model serves both FastAPI I/O and Strands `structured_output()`
- `boto3` / Bedrock inference-profile model IDs (`us.anthropic.claude-sonnet-4-6`) — pin `region_name` explicitly; bare foundation-model IDs commonly throw `ValidationException`
- Chrome MV3 (`host_permissions`, `background.js` service worker) — grants cross-origin fetch to localhost without needing broad CORS, but FastAPI `CORSMiddleware` should still be added for preflight `OPTIONS` handling

### Expected Features

Three stages, each with a table-stakes core, a differentiator, and explicit anti-features (all live integrations — Upwork scraping/API, live email/payment providers — are out of scope and structurally conflict with the demo's determinism requirement).

**Must have (table stakes):**
- Stage 1: structured field extraction, deterministic kill-switch gate (budget floor, client spend/hire-rate, red-flag keywords), LLM scorecard with reasoning — fully autonomous, zero escalation
- Stage 2: phased proposal, SOW with structured (machine-comparable) deliverables, milestone/payment schedule, `check_scope_clarity` with a single targeted escalation question on ambiguity
- Stage 3: `check_scope_creep` (LLM vs. structured SOW), `check_invoice_status` (pure deterministic date check), `draft_status_update`, each surfaced as a distinct escalation card
- Engagement Record shared state + visibly orchestrating Supervisor — both are top judging criteria, not just features

**Should have (competitive differentiators):**
- Legible split between deterministic-gate and LLM-judgment reasoning, visible in output (which layer produced the verdict)
- Escalations that are targeted/singular (one specific question) and structurally causal (they actually gate `/advance` behavior), not decorative UI

**Defer (v2+ / stretch):**
- Amazon Bedrock AgentCore deployment (explicit stretch, cut first under time pressure)
- Richer/varied fixtures, extended contract boilerplate
- Any live integration (Upwork API, email/calendar, payment providers) — permanently out of scope for this milestone, not just deferred

### Architecture Approach

A four-layer system: Chrome extension (capture) → FastAPI (HTTP contract + sole writer of state) → Supervisor Agent using Agents-as-Tools to route to exactly one of three specialist Agents per stage → a persisted Engagement Record (file/SQLite) as the only durable shared-state channel. No agent writes directly to the store; only FastAPI does, keeping a single auditable write path and avoiding concurrent-write races.

**Major components:**
1. **Chrome Extension (popup + background.js)** — paste-based capture UI; service worker owns `fetch()` to sidestep MV3 CORS/lifecycle restrictions; never talks to the LLM directly
2. **FastAPI backend** — single source of truth for the HTTP contract (`/capture`, `/engagements/{id}`, `/engagements/{id}/advance`); loads/saves the Engagement Record; the only caller of the Supervisor
3. **Supervisor Agent (Strands, Agents-as-Tools)** — routes a stage-scoped task to exactly one specialist per call via `.as_tool()`-wrapped sub-agents; must not re-author/paraphrase specialist output (use structured JSON contracts, not free-text delegation)
4. **Three specialist Agents (Gig Triage, Proposal-Contract, Ops)** — each its own `Agent` instance with its own system prompt and only its own `@tool` functions; this separation is itself a judging requirement
5. **Engagement Record store** — Pydantic-modeled JSON document per engagement, file-based for the demo (human-inspectable, zero setup); the durable shared-state channel, deliberately not Strands' in-process `Agent.state`/`invocation_state`

### Critical Pitfalls

1. **Guessing the Strands multi-agent API instead of verifying it** — do a dedicated Phase 0 spike (2-agent smoke test) confirming `.as_tool()` signature and delegation constraints against live docs before writing any specialist logic.
2. **Building a "single wrapped LLM call" that only looks multi-agent** — structurally enforce 4 distinct `Agent(...)` instantiations from day one and verify via trace inspection at each agent-implementation phase, not just at the end.
3. **Structured-output exceptions when the LLM wants to escalate instead of answering the schema** — the Proposal-Contract Agent's `needs_human_input`/`question` fields must be `Optional` from the start of schema design, with the ambiguous-fixture test exercised in the same phase as the happy path.
4. **LLM nondeterminism breaking the required repeatable demo** — push all verdict/escalation-triggering logic into deterministic Python (kill-switch, invoice date-check, SOW-deliverable diffing) and reserve the LLM for reasoning/prose only; run the full fixture set 3x before recording to confirm identical outputs.
5. **Decorative escalation design** — each of the three escalation points must have a defined Engagement Record field, a defined behavioral change in `/advance` when set, and a fixture pair (positive and negative case) proving it's conditional, not hardcoded or cosmetic.

## Implications for Roadmap

Based on research, suggested phase structure (7-8 phases, dependency-ordered):

### Phase 1: Foundations — Engagement Record + Strands API Verification Spike
**Rationale:** Everything downstream reads/writes the Engagement Record schema, and the Strands agents-as-tools routing mechanism is the highest-uncertainty, most-judged piece — both must be de-risked before any specialist agent logic is written.
**Delivers:** `models/engagement_record.py` (Pydantic schema with Optional escalation fields designed in from the start), `store/engagement_store.py` (file-based load/save interface), a throwaway 2-agent Strands smoke test proving `.as_tool()` routing works against the pinned SDK version, and a Bedrock connectivity smoke test (region/model-ID pinned explicitly).
**Addresses:** Engagement Record shared state (top judging criterion)
**Avoids:** Pitfall 1 (guessed API), Pitfall 2 (Bedrock region/credential mismatch), Pitfall 3 (schema not designed for escalation branches)

### Phase 2: Gig Triage Agent (standalone)
**Rationale:** Lowest-dependency specialist (no upstream stage needed); proves the deterministic-gate-then-LLM-judgment pattern Stage 3 will repeat, and is the fully autonomous stage — a good isolated slice to validate before adding orchestration complexity.
**Delivers:** `extract_job_fields`, `kill_switch_check` (pure Python, unit-testable without any LLM call), `llm_scorecard`, tested standalone against fixture job postings (no Supervisor, no API yet).
**Addresses:** Stage 1 table stakes (kill-switch gate, LLM scorecard, verdict/score/reasoning output)
**Avoids:** Pitfall 7 (LLM nondeterminism) — verified early by keeping verdict-gating logic deterministic

### Phase 3: Supervisor Wiring + `/capture` Endpoint (Stage 1 end-to-end)
**Rationale:** Proves the agents-as-tools routing pattern end-to-end on the smallest possible slice (one specialist) before adding the other two — the highest-risk, most-judged architectural piece.
**Delivers:** Supervisor Agent wrapping the Gig Triage Agent via `.as_tool()`; FastAPI `/capture` endpoint wired to Supervisor + Engagement Record store; a demoable capture→triage flow (still no extension).
**Uses:** `strands-agents` Agents-as-Tools pattern, FastAPI + Pydantic
**Implements:** Orchestration layer + API layer from the architecture doc

### Phase 4: Chrome Extension Capture UI
**Rationale:** Independent of Stages 2–3 once `/capture` is stable; can run in parallel with Phase 5, sequenced here because it depends on Phase 3's working endpoint and carries its own MV3-specific pitfalls.
**Delivers:** `manifest.json`, `popup.html/js`, `background.js` service worker performing the fetch; inline verdict/score/reasoning rendering; explicit pending-state UI.
**Addresses:** "Extension paste-capture + inline verdict" (P1 feature)
**Avoids:** Pitfall 5 (service-worker statelessness — test cold-start after idle), Pitfall 6 (host_permissions/CORS misconfiguration), Pitfall 9 (Upwork ToS drift — no URL-fetch convenience features)

### Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal")
**Rationale:** Requires Stage 1's verdict as input; its SOW schema is the single most important cross-stage dependency in the whole system — Stage 3's scope-creep detection has nothing to diff against if deliverables aren't structured here.
**Delivers:** `draft_proposal`, `draft_contract`, `check_scope_clarity`; structured SOW/milestone/payment-schedule output; `/engagements/{id}/advance` extended for stage="proposal"; escalation path tested against a deliberately ambiguous fixture.
**Addresses:** Stage 2 table stakes and the "escalation is targeted and singular" differentiator
**Avoids:** Pitfall 3 (structured-output exception on ambiguous input), Pitfall 8 (decorative escalation)

### Phase 6: Ops Agent + Stage 3 Fixtures
**Rationale:** Depends on Stage 2's structured SOW/payment schedule; fixtures must be authored with a deliberate scope-creep message and overdue milestone baked in before the Ops Agent is built.
**Delivers:** `check_scope_creep` (LLM vs. SOW), `check_invoice_status` (deterministic date check), `draft_status_update`; `/advance` extended for stage="ops" with fixture loading; both escalation cards verified to fire correctly and to NOT fire on clean fixtures.
**Addresses:** Stage 3 table stakes; the "second instance of the gate-then-judgment pattern" differentiator
**Avoids:** Pitfall 7 (nondeterminism — run fixtures 3x), Pitfall 8 (decorative escalation)

### Phase 7: Full Demo Run-through, Determinism Verification, and Documentation
**Rationale:** Nothing here is buildable until all three specialists and the extension are working; exists specifically to catch integration-level pitfalls (single-wrapped-call disguise, decorative escalations, nondeterminism) that individual phase tests can miss.
**Delivers:** End-to-end extension→triage→advance(proposal)→advance(ops) run recorded for timing; fixture set run 3x with diffed outputs; architecture diagram matched against the actual object graph; README, license, demo script.
**Addresses:** The submission checklist (README, license, architecture diagram, demo script) and the "looks done but isn't" verification checklist

### Phase 8 (Optional, cut-first): AgentCore Deployment
**Rationale:** Explicitly a stretch goal per PROJECT.md; sequenced strictly last and time-boxed so it can never consume schedule belonging to the core stages. Only attempted after Phase 7's file-based demo is fully working and recorded as a fallback.
**Delivers:** `AgentCoreMemorySessionManager` swapped in behind the `engagement_store` interface; Supervisor + specialists deployed to AgentCore Runtime — local file-based path kept fully functional as fallback throughout.
**Uses:** `bedrock-agentcore[strands-agents]` (LOW confidence, community-maintained)
**Implements:** The "Multi-user / stretch AgentCore deployment" scaling path from ARCHITECTURE.md

### Phase Ordering Rationale

- **Schema and orchestration risk come first (Phases 1–3):** the Engagement Record shape and the Strands agents-as-tools mechanism are hard dependencies for every later phase and the two most novel/unverified pieces — de-risking them early avoids expensive rework close to the deadline.
- **Extension is decoupled and can shift:** Phase 4 depends only on `/capture` being stable (Phase 3) and can proceed in parallel with Stage 2/3 agent work — flexible in exact ordering but shouldn't block it.
- **Stage 2 before Stage 3 is a hard dependency, not a preference:** Stage 3's scope-creep detection and invoice flagging both require Stage 2's structured SOW/payment schedule to exist first — the single most load-bearing cross-stage dependency in the whole system.
- **Integration/verification is its own phase, not folded into the last agent phase:** nondeterminism and decorative-escalation failures are systemic risks that only surface when the full pipeline runs together, so a dedicated Phase 7 catches what per-agent unit tests cannot.
- **AgentCore is isolated last with a hard gate:** every research file agrees this is optional, unverified, and the first thing PROJECT.md says to cut — sequencing it after a fully working fallback exists means a stalled AgentCore effort costs nothing already built.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Foundations/spike):** Strands multi-agent API surface is fast-moving and thinly documented on cross-pattern trade-offs; re-verify `.as_tool()` signature, delegation constraints, and `structured_output()` behavior against the SDK version actually pinned at build time.
- **Phase 8 (AgentCore, if pursued):** AgentCore Memory session-manager integration is explicitly community-maintained/unstable and its Runtime deployment mechanics were out of scope for this research pass — needs dedicated research before any integration code is written.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Gig Triage Agent):** deterministic gate + LLM scorecard is a well-established pattern (industry-standard freelance-vetting heuristics).
- **Phase 4 (Chrome Extension):** MV3 `host_permissions`/service-worker patterns are well-documented, stable Chrome platform behavior; the pitfalls are execution discipline, not unknown API surface.
- **Phase 5 & 6 (Proposal-Contract, Ops Agents):** FastAPI/Pydantic patterns are standard, long-stable API surface; the risk is schema design discipline, not missing documentation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH on Strands core/Bedrock/FastAPI/MV3; LOW on AgentCore Memory | Verified directly against strandsagents.com docs and PyPI; AgentCore explicitly self-flagged unstable by its own maintainers |
| Features | MEDIUM | PROJECT.md/PRD.md treated as primary source (detailed and authoritative); freelance-ops norms applied via domain knowledge given hackathon time budget |
| Architecture | HIGH | Multi-agent pattern and state-management guidance verified against official Strands docs; matches PRD's explicit judging criteria closely |
| Pitfalls | MEDIUM | Strands SDK facts verified against docs as of a Sept 2026 snapshot; SDK is actively evolving, so exact API names must be re-verified immediately before Phase 1 coding |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Exact Strands multi-agent call shape** (`.as_tool()` vs. direct list inclusion, `delegate=True` availability/constraints) verified only against a snapshot in time on a fast-moving SDK — Phase 1's spike must re-confirm against the exact pinned version before the Supervisor is built for real.
- **AgentCore Runtime deployment mechanics** (packaging/deploying a Strands agent as an AgentCore Runtime agent) were explicitly out of scope for this research pass — if Phase 8 is attempted, needs its own research cycle first.
- **Exact current Bedrock model ID/inference-profile string** for Claude must be confirmed against the team's AWS account's "Model access" console page at build time, not hardcoded from this research.
- **`structured_output()` exact exception behavior** was verified via search summary rather than a direct doc fetch — Phase 5's ambiguous-fixture test is the concrete verification step that resolves this gap in practice.

## Sources

### Primary (HIGH confidence)
- https://strandsagents.com/docs/user-guide/quickstart/python/ — install, minimal `Agent`, `@tool` decorator, Python 3.10+ requirement
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/agents-as-tools/ — verified supervisor/specialist code pattern
- https://strandsagents.com/docs/user-guide/concepts/multi-agent/swarm/ — Swarm import/constructor, why it's the wrong fit
- https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/ — `BedrockModel`, region/credential resolution
- https://strandsagents.com/docs/user-guide/concepts/agents/state/ — `Agent.state`/`invocation_state` scoping (why not to use as system of record)
- https://strandsagents.com/docs/integrations/session-managers/agentcore-memory/ — AgentCore Memory API + explicit "community-maintained" caveat
- https://pypi.org/project/strands-agents/ — current version 1.54.0 (2026-08-27)
- https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle — MV3 30s/5min termination behavior
- `/home/user/Freelance-Autopilot/.planning/PROJECT.md`, `/home/user/Freelance-Autopilot/docs/PRD.md` — primary product/requirements source

### Secondary (MEDIUM confidence)
- https://aws.amazon.com/blogs/machine-learning/multi-agent-collaboration-patterns-with-strands-agents-and-amazon-nova/ — multi-agent pattern deep dive
- https://aws.amazon.com/blogs/machine-learning/strands-agents-sdk-a-technical-deep-dive-into-agent-architectures-and-observability/ — architecture/observability
- https://dev.to/aws-heroes/5-multi-agent-patterns-in-strands-agents-which-one-and-when-48gh — pattern comparison
- General FastAPI CORS and Chrome MV3 `host_permissions` consensus (stable, long-standing platform behavior, not independently re-fetched in full)

### Tertiary (LOW confidence)
- AgentCore Runtime deployment mechanics — not independently verified, flagged for dedicated research if Phase 8 is pursued
- `structured_output()` exact exception/wrapping behavior — via search summary, not direct doc fetch; resolved practically via Phase 5's forced-ambiguous-fixture test

---
*Research completed: 2026-09-01*
*Ready for roadmap: yes*
