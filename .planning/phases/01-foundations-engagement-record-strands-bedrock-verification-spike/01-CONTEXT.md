# Phase 1: Foundations — Engagement Record & Strands/Bedrock Verification Spike - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase proves the two highest-uncertainty foundations before any specialist agent
is built: (1) the Engagement Record Pydantic schema + a persisted store with a single
writer path, and (2) that Strands multi-agent (agents-as-tools) wiring and the Bedrock
model provider actually work against the pinned SDK version. It delivers REC-01, REC-02,
REC-03, ORC-03. It does NOT build any real specialist agent, tool logic, HTTP endpoint,
or extension — those are later phases. The Strands/Bedrock work here is a throwaway smoke
test, not production agent code.

</domain>

<decisions>
## Implementation Decisions

Auto-selected (--auto mode) from the locked research in `.planning/research/` and PROJECT.md.

### Persistence (REC-02)
- **D-01:** Use file-based JSON persistence (one JSON file per `engagement_id` under a `data/engagements/` dir) behind an abstract `EngagementStore` interface with `create/get/save` methods. — **Reversibility:** reversible — SQLite or AgentCore Memory can implement the same interface later without touching callers.
- **D-02:** The store interface is the ONLY persistence seam; the concrete file store is swappable via a single construction point (dependency-injected into FastAPI). This is what lets Phase 8 (AgentCore) be a config change, not a rewrite.

### Engagement Record schema (REC-01)
- **D-03:** Model the Engagement Record as Pydantic v2 `BaseModel`s exactly matching PRD §6.2 (engagement_id, job, triage, proposal, contract, ops slices), with each stage slice optional/defaulted so a freshly-captured record is valid before later stages run. — **Reversibility:** costly — the shape is a shared contract between FastAPI I/O, Strands `structured_output()`, and every later phase; changing field names later touches all specialists.
- **D-04:** `engagement_id` is a server-generated UUID (uuid4) assigned at creation.

### Single-writer discipline (REC-03)
- **D-05:** Only FastAPI (the API layer) calls `EngagementStore.save`. Agents/tools return typed data; the API merges it into the record. Enforce with a module boundary + a test asserting no agent/tool module imports the store. — **Reversibility:** costly — this is the core determinism/architecture guarantee the judging narrative rests on.

### Strands + Bedrock wiring (ORC-03)
- **D-06:** Pin `strands-agents` (verified latest 1.54.0) and construct an explicit `BedrockModel(model_id=..., region_name=...)` — never rely on the bare-string model default — so model id and region are visible in code. Model id/region come from environment variables with documented defaults (e.g. `BEDROCK_MODEL_ID`, `AWS_REGION`).
- **D-07:** Use the **agents-as-tools** pattern (specialist `Agent` wrapped in an `@tool` function, passed into the supervisor's `tools=[...]`) — NOT Swarm (non-deterministic) or Graph (overkill). The Phase 1 smoke test builds a throwaway 2-agent version to confirm the pattern and independent tool-call traces.
- **D-08:** The Bedrock connectivity smoke test must **fail fast with a readable, diagnosable error** when credentials/region/model access are missing (this environment may lack AWS credentials). Do not hard-crash the whole app; surface a clear message. The smoke test is a standalone script, not part of the API's import path.

### Claude's Discretion
- Project/package layout under `backend/` (module names, whether to use a `src/` layout), test framework wiring (pytest + httpx), and the exact env-var names/defaults — planner/executor may choose idiomatic conventions consistent with the STACK research.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — project scope, constraints, key decisions
- `.planning/REQUIREMENTS.md` §Engagement Record & Persistence, §Orchestration — REC-01/02/03, ORC-03
- `docs/PRD.md` §6.2 — the exact Engagement Record JSON shape to model

### Verified stack/architecture (source of truth over training memory)
- `.planning/research/STACK.md` §1–4 — Strands package/version, agents-as-tools, `@tool`, `BedrockModel` wiring, `structured_output()`
- `.planning/research/ARCHITECTURE.md` — component boundaries, FastAPI-as-sole-writer, build order, shared-state pattern
- `.planning/research/PITFALLS.md` — guessed-API risk, single-wrapped-call risk, Bedrock region/credential traps, determinism
- `.planning/research/SUMMARY.md` — phase ordering rationale

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — this is the first code phase (repo currently holds only GSD tooling and planning docs).

### Established Patterns
- GSD workflow enforcement is active (`.claude/CLAUDE.md`); code changes flow through GSD phases.

### Integration Points
- The `EngagementStore` interface defined here is the integration seam every later phase (API, specialists, AgentCore) builds against.

</code_context>

<specifics>
## Specific Ideas

- STACK.md explicitly warns: use an inference-profile model id (`us.`/`global.` prefixed), verify the exact Claude slug against the account's Bedrock model access; do not hardcode a bare foundation-model id.
- PITFALLS.md: verify the current Strands `.as_tool()`/tools wiring with a throwaway 2-agent smoke test before writing real specialists — this phase IS that smoke test.

</specifics>

<deferred>
## Deferred Ideas

- SQLite persistence backend — deferred; file JSON is sufficient for the demo, and the interface makes SQLite a later drop-in.
- AgentCore Memory persistence — Phase 8 (optional, cut-first).

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Foundations — Engagement Record & Strands/Bedrock Verification Spike*
*Context gathered: 2026-09-01*
