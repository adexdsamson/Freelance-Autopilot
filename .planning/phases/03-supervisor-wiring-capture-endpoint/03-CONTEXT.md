# Phase 3: Supervisor Wiring + `/capture` Endpoint - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Mode:** Auto-generated (--only 3 autonomous run; decisions grounded in research + the Phase-2-not-built constraint)

<domain>
## Phase Boundary

This phase builds a real Strands **Supervisor** agent that orchestrates a Gig Triage
specialist via the **agents-as-tools** pattern, and exposes Stage 1 end-to-end through
FastAPI: `POST /capture` (create record → run triage via Supervisor → merge typed verdict
→ persist → return verdict) and `GET /engagements/{id}`. Delivers ORC-02, API-01, API-02.

**Explicit constraint — Phase 2 is NOT built yet** (this is an `--only 3` run). Phase 3
therefore wires the Supervisor to a **minimal placeholder Gig Triage specialist** behind a
stable seam. Phase 3 does NOT implement Phase 2's real triage logic (`extract_job_fields`,
`kill_switch_check`, `llm_scorecard`, TRI-01..04) — that stays Engineer B's Phase 2 work
and drops into the same seam without changing Phase 3's Supervisor/API code.

Out of scope: the real triage tools; the Chrome extension (Phase 4); proposal/ops stages.

</domain>

<decisions>
## Implementation Decisions

### Agents-as-tools wiring (ORC-02)
- **D-01:** Build the Supervisor with the verified agents-as-tools shape from STACK.md §2 — a specialist `Agent` wrapped in an `@tool`-decorated function, passed into the Supervisor's `tools=[...]`. Two distinct `Agent` instances (Supervisor + Gig Triage specialist) so a trace shows two invocations (success criterion 4). — **Reversibility:** costly — this is the core "genuine multi-agent orchestration" the judging rewards; changing it later touches every specialist.
- **D-02:** The Gig Triage specialist returns a strict typed `TriageResult` (verdict/score/reasoning/extracted_fields — the Engagement Record's triage slice shape). FastAPI merges that typed object into the record **verbatim**; the Supervisor's model must not re-author it (success criterion 3). Enforce by having the triage tool return structured data that FastAPI reads from the tool result / a typed channel, not by parsing the Supervisor's prose.

### Placeholder triage seam (Phase 2 gap)
- **D-03:** Define the triage seam as a single callable/tool with a fixed signature (raw job fields in → `TriageResult` out). Phase 3 ships a **deterministic placeholder** implementation (e.g. a rule-of-thumb stub: budget-floor + keyword check producing a verdict/score/reasoning) so `/capture` is exercisable and deterministic without Bedrock. Phase 2 replaces the placeholder body with the real `extract_job_fields`/`kill_switch_check`/`llm_scorecard` behind the same signature. — **Reversibility:** reversible — swapping the placeholder for the real agent is a body change behind a stable interface.
- **D-04:** Mark the placeholder clearly in code (name/docstring) as a Phase-2 stand-in so it is not mistaken for the real triage.

### FastAPI as sole writer (REC-03 upheld)
- **D-05:** `POST /capture` is the only path that creates + saves the record: it constructs the record, runs triage via the Supervisor, merges the typed `TriageResult` into the triage slice, saves through the `EngagementStore`, and returns the verdict. `GET /engagements/{id}` reads via the store and returns 404 for unknown ids. The store is dependency-injected (constructed once, per Phase 1's swap seam).

### Credential-less test strategy (sandbox has placeholder AWS creds)
- **D-06:** A genuine Supervisor routes to the triage tool via the LLM, which needs Bedrock at runtime. Offline tests (no creds) MUST still pass, so they verify: (a) the FastAPI app + Supervisor construct without error; (b) the `/capture` handler's record-creation + typed-merge + persist + verdict-return path works when the triage seam yields a `TriageResult` (drive it deterministically / inject the placeholder result — no live LLM); (c) `GET /engagements/{id}` round-trips; (d) the Supervisor has the triage specialist registered as a tool. The **live end-to-end orchestration through real Bedrock** (and the two-invocation trace, criterion 4) is a documented **manual** verification, exactly as in Phase 1. `/capture` must fail fast + readably (not 500 with a raw traceback) when Bedrock is unavailable.

### Claude's Discretion
- FastAPI app layout (`backend/api.py` vs an `app/` package), Pydantic request/response models, how the deterministic placeholder is toggled vs the live Supervisor path (e.g. env flag), test client wiring (httpx/TestClient). Choose idioms consistent with STACK.md §5.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — scope, constraints
- `.planning/REQUIREMENTS.md` §Orchestration, §Capture API — ORC-02, API-01, API-02
- `docs/PRD.md` §6.1–6.2 — the /capture data flow and Engagement Record shape

### Phase 1 foundation (this branch is based on it)
- `backend/models/engagement_record.py` — the Engagement Record + triage slice this phase populates
- `backend/store/engagement_store.py`, `backend/store/file_engagement_store.py` — the store `/capture` and `/engagements` use (sole-writer rule)
- `.planning/phases/01-foundations-engagement-record-strands-bedrock-verification-spike/01-01-SUMMARY.md` — what Phase 1 delivered

### Verified stack/architecture
- `.planning/research/STACK.md` §2 (agents-as-tools), §4 (BedrockModel), §5 (FastAPI/Pydantic)
- `.planning/research/ARCHITECTURE.md` — FastAPI-as-sole-writer, specialist typed-JSON merge
- `.planning/research/PITFALLS.md` — single-wrapped-call risk, Supervisor re-authoring anti-pattern, Bedrock cred traps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EngagementRecord` + `TriageSlice` (Phase 1) — the record `/capture` creates and the triage shape the specialist fills.
- `EngagementStore` / `FileEngagementStore` (Phase 1) — inject into FastAPI; the only writer path.
- `backend/scripts/smoke_test_agents_as_tools.py` (Phase 1) — the throwaway agents-as-tools shape to build the real Supervisor from.

### Established Patterns
- Single-writer rule enforced by `tests/test_single_writer.py` — the new `backend/api.py` (FastAPI) is the allowed writer; agents/tools still must not import the store. Keep triage placeholder/tool free of store imports.
- Bedrock calls fail fast + readably; never leak credentials (Phase 1 pattern).

### Integration Points
- The triage seam defined here is exactly what Phase 2 implements against.

</code_context>

<specifics>
## Specific Ideas

- Success criterion 4 (two distinct Agent invocations) is the anti-"single wrapped call" guard — the Supervisor and the triage specialist must be separate `Agent` instances, observable in a trace. Keep that structurally true even though the live trace is manual-only here.

</specifics>

<deferred>
## Deferred Ideas

- Real triage tools (`extract_job_fields`, `kill_switch_check`, `llm_scorecard`) — Phase 2 (Engineer B), behind the seam defined here.
- `/engagements/{id}/advance` (proposal/ops) — Phase 5/6.

None else — stayed within phase scope.

</deferred>

---

*Phase: 3-Supervisor Wiring + /capture Endpoint*
*Context gathered: 2026-09-01*
