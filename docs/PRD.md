# PRD: Freelance Autopilot

**Hackathon:** Agents for Humans (AWS Strands Agents SDK) — Professional Agents track
**Deadline:** Sep 14, 2026
**Author:** Adeola Adediran

## 1. Summary
Freelance Autopilot is an agentic system that owns the full lifecycle of a freelance engagement end to end: from deciding whether a gig is worth applying to, through drafting the proposal and contract, to running lightweight ops (status updates, scope-creep detection, invoice tracking) once the engagement is live. It is built as a supervisor agent orchestrating three specialist agents using the Strands Agents SDK, with a Chrome extension as the real-world capture point for Stage 1, and mocked/fixture data driving Stages 2 and 3 for a controllable demo. This project supersedes and absorbs the standalone "Gig Triage" hackathon submission (micro1) as its first stage.

## 2. Problem
Freelancers lose time and money at three points: (1) Triage — applying to bad-fit jobs wastes limited platform "Connects" and time; (2) Proposal/contract drafting — repetitive, judgment-heavy, easy to under-scope; (3) Ops during the engagement — scope creep goes unnoticed until it's a dispute, invoices go unpaid, status updates get forgotten.

## 3. Who it's for
Solo freelancers and independent consultants who take on multiple concurrent client engagements (primary persona: a frontend/full-stack freelance developer running Upwork + direct client work).

## 4. Goals
- Demonstrate a genuine multi-agent Strands architecture (supervisor + specialists), not a single wrapped LLM call.
- Provide a real capture mechanism (Chrome extension) for at least one stage.
- Show clear human-in-the-loop escalation points that are structurally justified (kill-switch gate, scope ambiguity, scope creep, overdue invoice).
- Ship something that runs deterministically for a 5-minute demo video.

## 5. Non-goals
- No live Upwork API integration (ToS risk). No live email/calendar/payment provider integration for Stages 2–3 in the demo. No production-grade auth, multi-tenant user management, or billing. No mobile app. Web/extension only.

## 6. Architecture
Chrome Extension (real capture) -> Backend API (FastAPI, hosts Strands agents) -> Supervisor Agent (Strands) orchestrating: Gig Triage Agent (verdict, score, reasoning), Proposal-Contract Agent (proposal.md, contract.md, payment schedule), Ops Agent (status updates, scope-creep flags, invoice alerts). Shared state: "Engagement Record" (JSON, persisted per engagement).

### 6.1 Data flow
1. User captures a job via the Chrome extension (paste URL/text). 2. Extension POSTs structured job data to backend /capture. 3. Supervisor invokes Gig Triage Agent -> verdict + writes to Engagement Record. 4. If verdict is apply, user (or auto-flow in demo) triggers Proposal-Contract Agent -> drafts proposal + contract + payment schedule; escalates only if scope/budget ambiguous. 5. Demo "time-jump": mocked client message thread and payment schedule are loaded. 6. Ops Agent runs against mocked thread/schedule -> flags scope creep, drafts status update, flags overdue invoice; each flag a distinct card.

### 6.2 Engagement Record shape
{ "engagement_id": "uuid", "job": { "title","description","budget","client_stats" }, "triage": { "verdict":"apply|skip","score":0,"reasoning" }, "proposal": { "text","needs_human_input":false,"question":null }, "contract": { "text","payment_schedule":[] }, "ops": { "status_updates":[],"scope_creep_flags":[],"invoice_flags":[] } }

## 7. Stage specs
### 7.1 Gig Triage Agent (fully autonomous, no escalation)
Tools: extract_job_fields (structured extraction from raw job text/URL paste), kill_switch_check (deterministic gate: budget floor, red-flag keywords, client spend/hire-rate thresholds), llm_scorecard (LLM reasoning over fit, competition, rate reasonableness). Output: { verdict, score, reasoning, extracted_fields }.
### 7.2 Proposal-Contract Agent (escalates on ambiguous scope/budget)
Tools: draft_proposal (phased-scope proposal generation, reuse software-dev-proposal pattern), draft_contract (SOW + milestones + payment terms), check_scope_clarity (flags missing budget, timeline, or deliverables). Output: { proposal, contract, payment_schedule, needs_human_input, question }.
### 7.3 Ops Agent (escalates on scope creep, overdue invoice, judgment-needed status)
Tools: check_scope_creep (compares incoming mocked client messages vs signed SOW), check_invoice_status (flags milestones overdue vs payment schedule), draft_status_update (client-ready status summary). Output: running log of status updates + escalation cards per flag.

## 8. Chrome extension spec (capture only, feeding Stage 1)
Manifest V3. Popup with a "paste job details" flow (paste-based, not DOM scraping). On submit: POST structured payload to backend /capture. Displays verdict + score + reasoning inline once Gig Triage responds. No auth needed for demo; single local API key. Files: manifest.json, popup.html/popup.js, background.js (service worker for the fetch, avoids CORS), styles.css.

## 9. Risk: Upwork scraping / ToS
Extension uses paste-based capture (user copies job text/URL; no auto-scrape of live DOM) to sidestep ToS risk.

## 10. Mocked data (Stages 2–3)
fixtures/sample_upwork_jobs.json (5–8 postings, mixed fit), fixtures/sample_client_thread.json (thread with a deliberate scope-creep message), fixtures/sample_payment_schedule.json (schedule with one overdue milestone).

## 11. Tech stack
Agent framework: Strands Agents SDK (Python). Backend: FastAPI hosting supervisor + sub-agents. Deployment: Amazon Bedrock AgentCore (stretch goal; supervisor + sub-agents as AgentCore agents; Engagement Record via AgentCore session/memory). Frontend: vanilla JS / Manifest V3. Storage: file-based or SQLite for Engagement Records in demo; AgentCore memory for cross-stage continuity. LLM: Claude via Bedrock.

## 12. Repo structure (to scaffold)
freelance-autopilot/ README.md, LICENSE (MIT or Apache-2.0), architecture-diagram.png, backend/ (agents/{supervisor,gig_triage_agent,proposal_contract_agent,ops_agent}.py, tools/{extract_job_fields,kill_switch_check,llm_scorecard,draft_proposal,draft_contract,check_scope_clarity,check_scope_creep,check_invoice_status,draft_status_update}.py, models/engagement_record.py, fixtures/{sample_upwork_jobs,sample_client_thread,sample_payment_schedule}.json, api.py (FastAPI: /capture, /engagements/{id}, /engagements/{id}/advance), requirements.txt), extension/ (manifest.json, popup.html, popup.js, background.js, styles.css), docs/demo-script.md.

## 13. Submission checklist
Text description; public repo w/ MIT or Apache license; README with setup; architecture diagram; demo video (max 5 min) covering problem, who, why, live walkthrough; AWS Builder ID; optional live demo link; bonus builder.aws.com post titled "Agents for Humans".

## 14. Success metrics
Working end-to-end run: extension capture -> triage verdict -> proposal/contract draft -> ops agent flags, no manual glue during demo. At least one escalation per stage where relevant. Judges see genuine Strands multi-agent orchestration, not a single-call wrapper.

## 15. Open risks / questions
Confirm Strands SDK's multi-agent/supervisor pattern and AgentCore session/memory API against current docs before implementation (verify via docs, not memory). Six-week timeline is tight; consider cutting AgentCore deployment to a stretch goal if time runs short.
