# Walking Skeleton — Freelance Autopilot

**Phase:** 1
**Generated:** 2026-09-01

## Capability Proven End-to-End

A backend developer can construct a Pydantic `EngagementRecord` (job-only), persist it
through the `EngagementStore` seam to `data/engagements/{engagement_id}.json`, reload it by
`engagement_id`, and get back an equivalent object — while the throwaway Strands
agents-as-tools wiring and Bedrock model provider are proven to either work or fail fast with
a readable, diagnosable error against the pinned `strands-agents==1.54.0`.

This is a **backend-only** foundations phase. There is no UI and no database server: the
"full stack" this skeleton exercises is `model → store interface → file backend → round-trip`,
plus the standalone Strands/Bedrock verification spike that de-risks the orchestration
mechanism every later phase depends on. UI is Phase 4; endpoints are Phase 3; AgentCore is
Phase 8.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language / runtime | Python 3.11 (project requires ≥3.10 for `strands-agents`) | Verified available (3.11.15); Strands quickstart mandates 3.10+ |
| Package layout | Flat packages under `backend/` (`models/`, `store/`, `agents/`, `tools/`, `scripts/`, `tests/`); pytest run from `backend/` with `pythonpath = ["."]` | Matches RESEARCH.md Recommended Project Structure and its `from models... import` / `from store... import` import style; keeps FastAPI (Phase 3) able to import the same packages |
| Data model | Pydantic v2 nested `BaseModel`s mirroring PRD §6.2, every stage slice `Optional=None` (D-03) | One schema serves FastAPI I/O + Strands `structured_output()` later; a job-only record must validate before triage runs |
| Persistence | File-based JSON, one file per `engagement_id`, behind an abstract `EngagementStore(ABC)` with a single concrete `FileEngagementStore` (D-01/D-02) | SQLite / AgentCore Memory later implement the same interface at one construction point without touching callers |
| ID generation | Server-generated `uuid4` via Pydantic `default_factory` (D-04) | Also the path-traversal mitigation — `_path()` only ever sees a validated `UUID` |
| Single-writer boundary | AST/import-graph pytest asserting no module under `backend/agents/` or `backend/tools/` imports the store (D-05, REC-03) | Encodes the determinism guarantee now, while `agents/`/`tools/` are empty placeholders, so Phase 2+ cannot violate it |
| Model provider | Explicit `BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION)` — never a bare model-id string (D-06, ORC-03) | Model id + region visible in code and env-driven; inference-profile-form id required by Bedrock |
| Orchestration mechanism | Agents-as-tools (`@tool`-wrapped specialist in supervisor `tools=[...]`) — NOT Swarm/Graph (D-07) | Deterministic, judgeable, "genuine multi-agent visible in code"; proven throwaway before real specialists |
| Deployment target | N/A this phase — local pytest + standalone smoke scripts only | Backend foundations phase; no server, no UI, no deploy |

## Stack Touched in Phase 1

- [x] Project scaffold (Python package layout, `backend/pyproject.toml` with pinned deps + pytest config)
- [ ] Routing — **N/A** (no HTTP surface until Phase 3 `/capture`)
- [x] Persistence — one real write (`FileEngagementStore.save`) AND one real read (`FileEngagementStore.get`) round-tripped in a test
- [ ] UI — **N/A** (Chrome extension is Phase 4)
- [ ] Deployment — **N/A** (documented local run: `cd backend && python -m pytest`; smoke scripts run with `python -m scripts.smoke_test_*`)
- [x] Orchestration spike — throwaway Strands agents-as-tools wiring + Bedrock fail-fast connectivity check (proves the highest-uncertainty mechanism)

## Out of Scope (Deferred to Later Slices)

- Any real specialist agent, tool business logic, or system prompt (Gig Triage is Phase 2)
- Any FastAPI endpoint (`/capture`, `/engagements/{id}`, `/advance` are Phase 3 / Phase 6)
- The Chrome extension (Phase 4)
- SQLite or AgentCore Memory persistence backends (deferred; the interface makes them a drop-in — Phase 8)
- A live, credential-backed Bedrock completion as a *gating* requirement — this sandbox has placeholder AWS credentials, so the fail-fast path is the expected PASS here (D-08)
- Fixtures for Stages 2–3 (Phase 6)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its
architectural decisions (the schema, the store seam, the agents-as-tools mechanism, the
explicit `BedrockModel` wiring):

- Phase 2: Gig Triage Agent (standalone) — real specialist `Agent` + `extract_job_fields` / `kill_switch_check` / `llm_scorecard` tools, validated against fixture jobs.
- Phase 3: Supervisor wires the Gig Triage Agent via agents-as-tools; `POST /capture` + `GET /engagements/{id}` expose Stage 1, FastAPI merging typed output into the record it owns.
- Phase 4: Chrome extension paste-capture popup posting to `/capture`.
- Phase 5: Proposal-Contract Agent + `/advance` (proposal) with structured escalation.
- Phase 6: Ops Agent, Stage 2–3 fixtures, full three-specialist supervisor wiring.
- Phase 7: End-to-end determinism verification + submission docs.
- Phase 8 (optional, cut-first): swap `FileEngagementStore` for AgentCore Memory behind the same interface.
