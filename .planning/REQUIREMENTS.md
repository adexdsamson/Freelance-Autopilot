# Requirements: Freelance Autopilot

**Defined:** 2026-09-01
**Core Value:** A freelancer captures a real job and the system runs it end to end through genuine multi-agent Strands orchestration — triage → proposal/contract → ops flags — with structurally justified human-in-the-loop escalations.

## v1 Requirements

Requirements for the hackathon submission. Each maps to roadmap phases.

### Engagement Record & Persistence

- [x] **REC-01**: A single Pydantic-typed Engagement Record models job, triage, proposal, contract, and ops slices per the PRD 6.2 shape.
- [x] **REC-02**: An Engagement Record is persisted per engagement to a durable store (file-based JSON or SQLite) behind a store interface, so stages invoked from separate HTTP requests share state.
- [x] **REC-03**: FastAPI is the sole writer that merges each specialist agent's typed output into the Engagement Record (agents do not mutate the record directly).

### Orchestration (Strands Supervisor)

- [ ] **ORC-01**: A Strands Supervisor agent orchestrates three distinct specialist Agent instances via the agents-as-tools pattern (four separately traceable agents, not one wrapped LLM call).
- [x] **ORC-02**: Each specialist returns strict typed JSON that FastAPI merges into the Engagement Record without the Supervisor re-authoring it.
- [x] **ORC-03**: Claude on Amazon Bedrock is wired as the Strands model provider with an explicit model id and region.

### Gig Triage (Stage 1 — autonomous)

- [ ] **TRI-01**: `extract_job_fields` produces structured fields (title, description, budget, client stats) from raw pasted job text/URL.
- [ ] **TRI-02**: `kill_switch_check` is a deterministic gate applying budget floor, red-flag keywords, and client spend/hire-rate thresholds.
- [ ] **TRI-03**: `llm_scorecard` reasons over fit, competition, and rate reasonableness to produce a score and reasoning.
- [ ] **TRI-04**: The Gig Triage Agent returns `{ verdict (apply|skip), score, reasoning, extracted_fields }` fully autonomously with no escalation.

### Capture API & Endpoints

- [x] **API-01**: `POST /capture` accepts a structured job payload, runs triage via the Supervisor, writes the result to a new Engagement Record, and returns the verdict.
- [x] **API-02**: `GET /engagements/{id}` returns the current Engagement Record.
- [ ] **API-03**: `POST /engagements/{id}/advance` advances the engagement to the next stage (proposal/contract, then ops) and returns the updated record.

### Chrome Extension (capture client)

- [ ] **CAP-01**: A Manifest V3 extension popup provides a paste-based capture flow (no live DOM scraping) and submits the job payload.
- [ ] **CAP-02**: The extension `background.js` service worker POSTs the payload to the backend `/capture` endpoint (host_permissions scoped to the backend origin).
- [ ] **CAP-03**: The popup displays the returned triage verdict, score, and reasoning inline once the agent responds.

### Proposal-Contract (Stage 2 — escalates on ambiguity)

- [x] **PROP-01**: `draft_proposal` generates a phased-scope proposal for an `apply` engagement.
- [x] **PROP-02**: `draft_contract` generates a contract (SOW with enumerable deliverables + milestones + payment terms).
- [x] **PROP-03**: A structured payment schedule is produced alongside the contract.
- [x] **PROP-04**: `check_scope_clarity` flags missing budget, timeline, or deliverables, and the agent returns `needs_human_input` + a specific `question` rather than guessing when scope/budget is ambiguous.

### Ops (Stage 3 — escalates on creep / overdue)

- [ ] **OPS-01**: `check_scope_creep` compares incoming (fixture) client messages against the signed SOW's deliverables and flags creep.
- [ ] **OPS-02**: `check_invoice_status` flags milestones overdue against the payment schedule.
- [ ] **OPS-03**: `draft_status_update` generates a client-ready status summary.
- [ ] **OPS-04**: Each scope-creep flag, invoice flag, and judgment-needed status is surfaced as a distinct escalation card in the Ops output.

### Fixtures, Demo & Submission

- [ ] **DEMO-01**: Fixtures seed Stages 2–3 deterministically: sample jobs (mixed fit), a client thread containing a deliberate scope-creep message, and a payment schedule with one overdue milestone.
- [ ] **DEMO-02**: The end-to-end run (extension capture → triage → proposal/contract → ops flags) completes with no manual glue steps and repeats deterministically.
- [ ] **DEMO-03**: README documents setup and run instructions.
- [ ] **DEMO-04**: An OSI license (MIT or Apache-2.0) is present at the repo root.
- [ ] **DEMO-05**: An architecture diagram and a demo script (docs/demo-script.md) are included.

## v2 Requirements

Deferred beyond the hackathon submission.

### Deployment

- **DEPLOY-01**: Deploy the Supervisor and specialists as Amazon Bedrock AgentCore agents.
- **DEPLOY-02**: Persist the Engagement Record via AgentCore session/memory primitives for cross-stage continuity.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Live Upwork API / DOM scraping | Upwork ToS risk; paste-based capture used instead |
| Live email / calendar / payment integration for Stages 2–3 | Out of demo scope; fixtures drive these stages |
| Auto-send of proposals/contracts/status updates | Human-in-the-loop by design; system drafts, human sends |
| Production auth, multi-tenant users, billing | Single local API key suffices for the demo |
| Mobile app | Web/extension only |

## Traceability

Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REC-01 | Phase 1 | Complete |
| REC-02 | Phase 1 | Complete |
| REC-03 | Phase 1 | Complete |
| ORC-03 | Phase 1 | Complete |
| TRI-01 | Phase 2 | Pending |
| TRI-02 | Phase 2 | Pending |
| TRI-03 | Phase 2 | Pending |
| TRI-04 | Phase 2 | Pending |
| ORC-02 | Phase 3 | Complete |
| API-01 | Phase 3 | Complete |
| API-02 | Phase 3 | Complete |
| CAP-01 | Phase 4 | Pending |
| CAP-02 | Phase 4 | Pending |
| CAP-03 | Phase 4 | Pending |
| PROP-01 | Phase 5 | Complete |
| PROP-02 | Phase 5 | Complete |
| PROP-03 | Phase 5 | Complete |
| PROP-04 | Phase 5 | Complete |
| ORC-01 | Phase 6 | Pending |
| API-03 | Phase 6 | Pending |
| OPS-01 | Phase 6 | Pending |
| OPS-02 | Phase 6 | Pending |
| OPS-03 | Phase 6 | Pending |
| OPS-04 | Phase 6 | Pending |
| DEMO-01 | Phase 6 | Pending |
| DEMO-02 | Phase 7 | Pending |
| DEMO-03 | Phase 7 | Pending |
| DEMO-04 | Phase 7 | Pending |
| DEMO-05 | Phase 7 | Pending |
| DEPLOY-01 (v2) | Phase 8 (optional) | Deferred |
| DEPLOY-02 (v2) | Phase 8 (optional) | Deferred |

**Coverage:**

- v1 requirements: 29 total (corrected from a stale count of 25 in this file's original draft — recounted directly against the REQ-IDs listed above)
- Mapped to phases: 29/29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-01*
*Last updated: 2026-09-02 after Phase 3 (ORC-02, API-01, API-02 complete)*
