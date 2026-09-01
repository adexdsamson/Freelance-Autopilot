# Freelance Autopilot

## What This Is

Freelance Autopilot is an agentic system that owns the full lifecycle of a freelance
engagement end to end — from deciding whether a gig is worth applying to, through
drafting the proposal and contract, to running lightweight ops (status updates,
scope-creep detection, invoice tracking) once the engagement is live. It is built as a
supervisor agent orchestrating three specialist agents on the Strands Agents SDK, with a
Manifest V3 Chrome extension as the real-world capture point for Stage 1 and fixture data
driving Stages 2–3 for a controllable demo. It is a hackathon submission for the "Agents
for Humans" (AWS Strands Agents SDK) Professional Agents track and supersedes the
standalone "Gig Triage" (micro1) submission as its first stage.

## Core Value

A freelancer captures a real job posting and the system runs it end to end through
genuine multi-agent Strands orchestration — triage verdict → proposal/contract draft →
live-engagement ops flags — with human-in-the-loop escalations that are structurally
justified, not decorative.

## Business Context

<!-- OPTIONAL — hackathon submission, not a monetized product. -->

- **Customer**: Solo freelancers and independent consultants running multiple concurrent client engagements.
- **Revenue model**: None (hackathon demo). Value is time saved and disputes/unpaid-invoices avoided.
- **Success metric**: A working, deterministic end-to-end run demonstrated in a ≤5-minute video with no manual glue steps.
- **Strategy notes**: See docs/PRD.md for the full product requirements.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Chrome extension (Manifest V3) captures a job via paste-based flow and POSTs structured data to the backend `/capture` endpoint.
- [ ] Extension displays the triage verdict, score, and reasoning inline in the popup once the Gig Triage Agent responds.
- [ ] Supervisor Agent (Strands) orchestrates three specialist sub-agents over a shared Engagement Record.
- [ ] Gig Triage Agent runs `extract_job_fields`, a deterministic `kill_switch_check` gate, and an `llm_scorecard`, returning `{ verdict, score, reasoning, extracted_fields }` fully autonomously (no escalation by design).
- [ ] Proposal-Contract Agent drafts a phased-scope proposal, a contract (SOW + milestones + payment terms), and a payment schedule; escalates a specific question to the human only when scope/budget is ambiguous.
- [ ] Ops Agent detects scope creep against the signed SOW, flags overdue invoice milestones, and drafts client-ready status updates — surfacing each flag as a distinct escalation card.
- [ ] Engagement Record (JSON) persists per engagement and is the shared state across all stages.
- [ ] FastAPI backend exposes `/capture`, `/engagements/{id}`, and `/engagements/{id}/advance`.
- [ ] Deterministic fixtures seed Stages 2–3: sample jobs, a client thread with a deliberate scope-creep message, and a payment schedule with one overdue milestone.
- [ ] Repository ships with README (setup instructions), an OSI license (MIT or Apache-2.0), an architecture diagram, and a demo script.

### Out of Scope

- Live Upwork API integration — Upwork ToS risk; paste-based capture is used instead.
- Automated DOM scraping of live job pages — ToS risk; the extension reads user-pasted text only.
- Live email/calendar/payment provider integration for Stages 2–3 — out of demo scope; fixtures drive these stages.
- Production-grade auth, multi-tenant user management, billing — a single local API key suffices for the demo.
- Mobile app — web/extension only.
- Amazon Bedrock AgentCore deployment — a stretch goal that strengthens but does not gate the technical score; cut first if the timeline slips.

## Context

- **Framework**: Strands Agents SDK (Python). The exact supervisor/multi-agent pattern and any AgentCore session/memory API surface must be verified against current Strands + AgentCore docs before implementation — not assumed from training data.
- **Backend**: FastAPI hosting the supervisor and sub-agents.
- **LLM**: Claude via Amazon Bedrock (consistent with the AWS-hosted stack).
- **Storage**: File-based or SQLite Engagement Records for the demo; AgentCore memory only if the stretch deployment is pursued.
- **Extension**: Vanilla JS, Manifest V3, no framework. `background.js` service worker performs the fetch to avoid CORS.
- **Prior art**: The Gig Triage pipeline (micro1) and the `software-dev-proposal` pattern are reused/adapted for Stages 1 and 2.
- **Judging**: Genuine Strands multi-agent orchestration (supervisor + specialists) must be visible in both the architecture diagram and the code — not a single wrapped LLM call.

## Constraints

- **Timeline**: Hackathon deadline Sep 14, 2026 — roughly six weeks; tight for three agent stages + extension + optional AgentCore deploy + video.
- **Tech stack**: Strands Agents SDK, FastAPI, Claude via Bedrock, Manifest V3 vanilla JS.
- **Compliance**: No automated scraping of Upwork; paste-based capture only (ToS).
- **Demo**: Must run deterministically for a ≤5-minute recorded walkthrough; fixtures make Stages 2–3 repeatable.
- **Licensing**: Public repo with an MIT or Apache-2.0 license visible in the About section (submission rule).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Supervisor + 3 specialist agents (not one wrapped call) | Judging criteria reward genuine multi-agent Strands orchestration | — Pending |
| Paste-based capture in the extension | Sidesteps Upwork ToS/scraping risk with minimal added friction | — Pending |
| Fixtures drive Stages 2–3 | Deterministic, repeatable 5-minute demo without live integrations | — Pending |
| Escalations only where structurally justified (scope ambiguity, scope creep, overdue invoice) | Human-in-the-loop must be meaningful, not decorative | — Pending |
| AgentCore deployment as a stretch goal | Strengthens but does not gate the technical score; first to cut if time slips | — Pending |
| Verify Strands/AgentCore APIs against live docs before building | SDK surface changes; avoid building on assumed APIs | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-01 after initialization*
