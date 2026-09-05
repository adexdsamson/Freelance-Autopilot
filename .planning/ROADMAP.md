# Roadmap: Freelance Autopilot

## Overview

Freelance Autopilot moves from zero to a fully demoable, deterministic three-stage agentic
pipeline in eight phases. The first three phases de-risk the two hardest, most-judged pieces —
the shared Engagement Record schema and the Strands agents-as-tools orchestration mechanism —
by proving them on the smallest possible slice (one specialist agent) before any UI or
second/third specialist exists. The middle phases add the Chrome extension capture client and
build out the Proposal-Contract and Ops specialists in their required dependency order (Stage 3's
scope-creep detection cannot exist without Stage 2's structured SOW). The system is now a real
supervisor orchestrating three distinct specialist agents over one shared Engagement Record. The
final two phases harden the whole pipeline for judging and submission (determinism verification,
docs, license, demo script) and then — only if time remains — attempt the optional AgentCore
deployment stretch, sequenced last and structured to cost nothing already built if it's cut.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike** - Establish the shared Engagement Record schema/store and prove the Strands agents-as-tools mechanism and Bedrock wiring before any specialist agent logic is written.
- [ ] **Phase 2: Gig Triage Agent (standalone)** - Build and validate the fully autonomous Stage 1 specialist (deterministic gate + LLM scorecard) against fixture jobs, with no Supervisor or API yet.
- [ ] **Phase 3: Supervisor Wiring + `/capture` Endpoint** - Wire the Supervisor to the Gig Triage Agent via agents-as-tools and expose `/capture` + `GET /engagements/{id}`, proving Stage 1 end-to-end.
- [ ] **Phase 4: Chrome Extension Capture UI** - Ship the Manifest V3 paste-based capture popup that posts to `/capture` and renders the triage verdict inline.
- [ ] **Phase 5: Proposal-Contract Agent + `/advance` (proposal)** - Build the Stage 2 specialist that drafts proposal/contract/payment schedule and escalates on scope/budget ambiguity.
- [ ] **Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring** - Build the Stage 3 specialist (scope creep, invoice, status update), wire it as the Supervisor's third tool, and author the deterministic Stage 2-3 fixture set.
- [ ] **Phase 7: Full Demo Verification & Submission Docs** - Verify the end-to-end pipeline runs deterministically within the 5-minute demo window and complete the submission checklist (README, license, diagram, demo script).
- [ ] **Phase 8: AgentCore Deployment (optional, cut-first)** - Swap the Engagement Record store to AgentCore Memory and deploy the Supervisor/specialists to AgentCore Runtime, only after Phase 7's local demo is fully working, with the local path kept as fallback.

## Phase Details

### Phase 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike

**Mode:** mvp
**Goal**: The Engagement Record schema/store and the Strands multi-agent + Bedrock wiring are proven to work before any specialist agent is built on top of them.
**Depends on**: Nothing (first phase)
**Requirements**: REC-01, REC-02, REC-03, ORC-03
**Success Criteria** (what must be TRUE):

  1. A developer can create, save, and reload an Engagement Record for a given engagement_id through the store interface and get back an equivalent Pydantic object.
  2. The Engagement Record store interface has exactly one caller path in the codebase (FastAPI) — no agent or tool writes to it directly.
  3. A throwaway two-agent Strands smoke test shows a supervisor routing to a distinct specialist agent, with independent tool-call trace entries for each.
  4. A Bedrock connectivity smoke test successfully calls Claude using an explicitly pinned model id and region, or fails fast with a readable, diagnosable error.

**Plans:** 0/1 plans executed

- [ ] 01-PLAN.md
- [x] 01-01-PLAN.md — Scaffold backend, Engagement Record model + file store round-trip (REC-01/02), single-writer AST test (REC-03), Strands agents-as-tools + Bedrock fail-fast smoke spike (ORC-03)

### Phase 2: Gig Triage Agent (standalone)

**Mode:** mvp
**Goal**: The fully autonomous Stage 1 specialist — deterministic gate followed by LLM judgment — works correctly and repeatably against fixture jobs, independent of the Supervisor or API.
**Depends on**: Phase 1
**Requirements**: TRI-01, TRI-02, TRI-03, TRI-04
**Success Criteria** (what must be TRUE):

  1. Given raw pasted job text, `extract_job_fields` returns structured fields (title, description, budget, client stats).
  2. `kill_switch_check` deterministically rejects or flags a fixture job that fails the budget floor, contains red-flag keywords, or has weak client spend/hire-rate stats, verified by a unit test that makes no LLM call.
  3. `llm_scorecard` produces a score and reasoning for a fixture job's fit, competition, and rate reasonableness.
  4. Running the Gig Triage Agent standalone against a fixture job returns `{ verdict, score, reasoning, extracted_fields }` with no escalation fields present anywhere in the output.

**Plans**: TBD

### Phase 3: Supervisor Wiring + `/capture` Endpoint

**Mode:** mvp
**Goal**: A real Strands Supervisor Agent orchestrates the Gig Triage Agent via agents-as-tools, and Stage 1 is reachable end-to-end through FastAPI.
**Depends on**: Phase 1, Phase 2
**Requirements**: ORC-02, API-01, API-02
**Success Criteria** (what must be TRUE):

  1. `POST /capture` with a structured job payload creates a new Engagement Record, runs triage through the Supervisor, and returns the verdict.
  2. `GET /engagements/{id}` returns the persisted record with the triage slice populated exactly as the specialist produced it.
  3. The Gig Triage Agent's typed JSON output reaches the Engagement Record unmodified — the Supervisor's model does not re-author or paraphrase it before FastAPI merges it in.
  4. Trace/log inspection of one `/capture` call shows two distinct Agent invocations (Supervisor and Gig Triage), not one flat call.

**Plans**: TBD

### Phase 4: Chrome Extension Capture UI

**Mode:** mvp
**Goal**: A freelancer can capture a real job posting from the browser via paste-based input and see the triage verdict inline, with no live scraping.
**Depends on**: Phase 3
**Requirements**: CAP-01, CAP-02, CAP-03
**Success Criteria** (what must be TRUE):

  1. A user can open the extension popup, paste job text, and submit it, with no live DOM scraping or backend URL-fetch convenience feature involved.
  2. The `background.js` service worker POSTs the payload to `/capture` and completes the round trip after a cold start (DevTools closed, idle more than 30 seconds).
  3. The popup shows an explicit pending state while waiting, then renders the returned verdict, score, and reasoning inline once the agent responds.

**Plans**: TBD
**UI hint**: yes

### Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal")

**Mode:** mvp
**Goal**: For an `apply`-verdict engagement, the system drafts a phased proposal and a contract with an enumerable-deliverables SOW, or asks one targeted question when scope/budget is genuinely ambiguous.
**Depends on**: Phase 3
**Requirements**: PROP-01, PROP-02, PROP-03, PROP-04
**Success Criteria** (what must be TRUE):

  1. Advancing a clear-scope, apply-verdict engagement to `stage="proposal"` returns a phased-scope proposal, a contract (SOW with enumerable deliverables + milestones + payment terms), and a structured payment schedule.
  2. Advancing a deliberately ambiguous fixture (missing budget, timeline, or deliverables) to the same stage returns `needs_human_input=true` with a specific `question`, instead of a guessed proposal/contract, and without raising a structured-output exception.
  3. No single response contains both a fully populated contract and `needs_human_input=true` — the happy path and the escalation path are mutually exclusive outcomes of the same schema.
  4. The Engagement Record's `proposal` and `contract` slices are populated only via FastAPI's merge of the specialist's typed output, never written by the agent directly.

**Plans**: TBD

### Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring

**Mode:** mvp
**Goal**: The Supervisor now orchestrates all three specialist agents, and the live-engagement Ops specialist correctly and conditionally flags scope creep and overdue invoices against deterministic fixtures.
**Depends on**: Phase 5
**Requirements**: ORC-01, API-03, OPS-01, OPS-02, OPS-03, OPS-04, DEMO-01
**Success Criteria** (what must be TRUE):

  1. The Supervisor's tools list contains all three specialist agents (Gig Triage, Proposal-Contract, Ops), each independently visible as a distinct traceable invocation in a run's trace/telemetry — four agents total, not one wrapped call.
  2. Advancing an engagement to `stage="ops"` against the fixture client thread and payment schedule flags the deliberate scope-creep message and the one overdue milestone as two distinct escalation cards.
  3. Running the same checks against a "clean" fixture variant (no creep, no overdue milestone) produces zero escalation cards, proving the checks are conditional rather than hardcoded.
  4. `draft_status_update` produces a client-ready status summary that reflects whatever flags are currently active.
  5. `POST /engagements/{id}/advance` correctly routes to and completes both the `proposal` and `ops` stages, returning the updated record each time.

**Plans**: TBD

### Phase 7: Full Demo Verification & Submission Docs

**Mode:** mvp
**Goal**: The complete pipeline is proven deterministic and demo-ready, and the repository satisfies every submission requirement.
**Depends on**: Phase 4, Phase 6
**Requirements**: DEMO-02, DEMO-03, DEMO-04, DEMO-05
**Success Criteria** (what must be TRUE):

  1. The full pipeline (extension capture → triage → advance-to-proposal → advance-to-ops) runs end to end with no manual glue steps, inside the 5-minute demo window.
  2. Running the full fixture set three times produces identical verdicts, escalation triggers, and flags across all three runs.
  3. The repo root has a visible OSI license (MIT or Apache-2.0) and a README with clear setup and run instructions.
  4. An architecture diagram matching the actual object graph and a `docs/demo-script.md` are both present in the repository.

**Plans**: TBD

### Phase 8: AgentCore Deployment (optional, cut-first)

**Mode:** mvp
**Goal**: The Supervisor and specialists can optionally run on Amazon Bedrock AgentCore with session/memory-backed persistence, without ever risking the working local demo.
**Depends on**: Phase 7
**Requirements**: None (v1 fully covered by Phases 1-7). Addresses v2 requirements DEPLOY-01, DEPLOY-02.
**Success Criteria** (what must be TRUE):

  1. The Engagement Record store can be swapped to `AgentCoreMemorySessionManager` behind the existing store interface without any change to agent or API code.
  2. The Supervisor and specialists, deployed to AgentCore Runtime, can process a capture-through-advance flow against a live AgentCore Memory session.
  3. The local file-based Engagement Record path still works end to end (re-running Phase 7's demo) even if this phase is abandoned or reverted mid-way.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (Phase 8 optional, cut first if timeline slips)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations — Engagement Record & Strands/Bedrock Verification Spike | 0/1 | Planned    |  |
| 2. Gig Triage Agent (standalone) | 0/TBD | Not started | - |
| 3. Supervisor Wiring + `/capture` Endpoint | 0/TBD | Not started | - |
| 4. Chrome Extension Capture UI | 0/TBD | Not started | - |
| 5. Proposal-Contract Agent + `/advance` (proposal) | 0/TBD | Not started | - |
| 6. Ops Agent, Fixtures & Full Supervisor Wiring | 0/TBD | Not started | - |
| 7. Full Demo Verification & Submission Docs | 0/TBD | Not started | - |
| 8. AgentCore Deployment (optional, cut-first) | 0/TBD | Not started | - |
