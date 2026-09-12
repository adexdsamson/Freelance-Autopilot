# Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal") - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning
**Mode:** Auto-generated (`--only 5` autonomous run, `--auto` discuss; decisions grounded in research, PRD §7.2, and the Phase-3 seam/placeholder/sole-writer precedent)

<domain>
## Phase Boundary

This phase builds the Stage 2 **Proposal-Contract specialist** and exposes it end-to-end
through FastAPI at `POST /engagements/{id}/advance` for `stage="proposal"`. For an
`apply`-verdict engagement it drafts a **phased-scope proposal**, a **contract** (SOW with
**enumerable deliverables + milestones + payment terms**), and a **structured payment
schedule**; when scope/budget is genuinely ambiguous it escalates with
`needs_human_input=true` + a specific `question` instead of guessing. Delivers PROP-01,
PROP-02, PROP-03, PROP-04.

**Explicit constraint — depends on Phase 3, stacked on `gsd/phase-03`.** This is an
`--only 5` run; the branch `gsd/phase-05-proposal-contract-agent-advance-stage-proposal`
is forked from `gsd/phase-03` (carries the Engagement Record, store, Supervisor, Gig
Triage specialist, `/capture`, `/engagements/{id}`). Phase 4 (Chrome extension) is NOT a
dependency and is not built here.

**Out of scope (belongs to later phases):**
- The full three-agent Supervisor (ORC-01) — Phase 6.
- `stage="ops"` advancing and the formal completion of API-03 (both proposal + ops) — Phase 6.
- The Ops specialist, scope-creep/invoice tooling, and the Stage 2–3 fixture set (DEMO-01) — Phase 6.
- LLM-authored prose quality: the live Bedrock path exists behind the seam, but the demo/tests run the deterministic path.

</domain>

<decisions>
## Implementation Decisions

### Structured-output schema — mutually-exclusive happy path vs escalation (PROP-04, SC2/SC3)
- **D-01:** The Proposal-Contract specialist returns ONE strict typed result whose two
  outcomes are **mutually exclusive**: either the happy path (a populated proposal +
  contract + structured payment schedule) OR the escalation path
  (`needs_human_input=true` + a specific `question`, with no populated contract). No single
  response carries both a fully populated contract and `needs_human_input=true` (SC3).
  `needs_human_input`/`question` are **first-class optional fields from the start** so the
  deliberately ambiguous fixture escalates cleanly and never raises a structured-output
  exception (SC2; STATE.md Phase-5 blocker). — **Reversibility:** costly — this schema is
  the contract FastAPI merges and every proposal-stage test asserts against; changing its
  shape later touches the specialist, the merge, and the tests together.

### Deterministic-first specialist behind a runner seam (mirrors Phase 3)
- **D-02:** Mirror Phase 3's `TriageRunner` DI seam exactly with a `ProposalRunner` seam
  (raw record/job in → typed proposal-contract result out). Ship a **deterministic
  default** implementation (template-driven proposal/contract + a deterministic
  scope-clarity gate) so `/advance` is exercisable and **deterministic offline** without
  Bedrock (aligns with DEMO-02 repeatability and the sandbox's placeholder AWS creds), and
  a **live supervisor/agent path** selected by a `PROPOSAL_BACKEND` env flag (default =
  deterministic). — **Reversibility:** reversible — swapping the deterministic body for the
  live agent is a body change behind a stable interface.

### Real Stage-2 tools (PRD §7.2), deterministic bodies, dual-use, no store import
- **D-03:** Build the three PRD §7.2 tools as the ONE source of truth for their rules,
  `@tool`-decorated so they are callable both as plain Python (deterministic path) and
  registered on the specialist Agent (live path) — the same dual-use pattern as
  `backend/tools/placeholder_triage.py`:
  - `check_scope_clarity` — a **deterministic gate** (no LLM) flagging missing budget,
    timeline, or deliverables; fully offline-testable like `kill_switch_check`.
  - `draft_proposal` — a **phased-scope** proposal.
  - `draft_contract` — an SOW with **enumerable deliverables + milestones + payment terms**.
  None of these import the store (single-writer guard, REC-03 — `test_single_writer.py`
  scans `backend/tools/` and `backend/agents/`).

### Genuine second specialist via agents-as-tools — without pre-doing Phase 6
- **D-04:** Wire a **distinct** Proposal-Contract `Agent` instance into a Supervisor via the
  same agents-as-tools shape Phase 3 proved (two distinct Agent instances, observable as
  separate invocations in a live trace). Do **not** prematurely implement ORC-01's full
  three-agent Supervisor (Phase 6) — extend only what the proposal stage needs behind the
  seam. — **Reversibility:** reversible — Phase 6 folds this specialist into the unified
  three-agent Supervisor.

### FastAPI as the sole writer of the proposal/contract slices (REC-03, SC4)
- **D-05:** `POST /engagements/{id}/advance` is the ONLY path that mutates the `proposal`
  and `contract` slices. It: loads the record (404 if unknown); **guards** that triage
  exists and `verdict == "apply"` (otherwise a 4xx — cannot draft a proposal for a
  skipped/untriaged engagement); runs the specialist via the `ProposalRunner` DI seam;
  merges the typed result **VERBATIM** into `proposal` (+ `contract` on the happy path)
  without the Supervisor re-authoring it; persists via the existing `store.save(record)`;
  returns the updated record. Structure the handler so Phase 6 adds `stage="ops"` without a
  rewrite. Reuse Phase 3's `map_bedrock_error` → readable, credential-free **503** on any
  Bedrock failure. — **Reversibility:** costly — the endpoint shape and status-code
  contract are what Phase 6 and any client build on.

### Structured (typed) payment schedule (PROP-03, SC1)
- **D-06:** Produce a **structured** payment schedule (typed milestones — e.g.
  label/amount/due-marker — not free prose) so SC1's "structured payment schedule" is
  machine-checkable and demo-deterministic. The current `ContractSlice.payment_schedule`
  (`list[dict]`) may be tightened to a typed milestone model; enriching the Phase-1 stub is
  in scope. — **Reversibility:** costly — persisted record shape; a change is a stored-JSON
  migration once records exist.

### Credential-less test strategy (sandbox has placeholder AWS creds) — same as Phase 3 D-06
- **D-07:** Offline tests (no creds) MUST pass and verify: (a) the deterministic path
  yields a valid proposal + contract + structured payment schedule for a **clear-scope**
  apply fixture (SC1); (b) a **deliberately ambiguous** fixture (missing budget, timeline,
  or deliverables) yields `needs_human_input=true` + a specific `question` and raises **no**
  structured-output exception (SC2); (c) **mutual exclusivity** holds — never a full
  contract alongside `needs_human_input=true` (SC3); (d) the merge is FastAPI-only and the
  slices reach the record verbatim (SC4); (e) `/advance` guards non-apply/unknown
  engagements; (f) the app + Supervisor + Proposal-Contract Agent construct without creds;
  (g) `/advance` fails fast + readably (503, never a raw 500) when the live path raises.
  The **live two-agent Bedrock trace** is a documented **manual** verification, exactly as
  in Phases 1 and 3.

### Claude's Discretion
- Module layout (`backend/agents/proposal_contract_agent.py`, `backend/agents/proposal_runner.py`,
  `backend/tools/{draft_proposal,draft_contract,check_scope_clarity}.py` per PRD §12, vs
  consolidating), the exact typed result model name/shape, the precise 4xx code for the
  non-apply guard (409 vs 422), the deterministic template wording, and whether the live
  path extends `build_supervisor()` or uses a stage-scoped builder — all at Claude's
  discretion, consistent with the Phase 3 idioms.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — scope, constraints, key decisions
- `.planning/REQUIREMENTS.md` §Proposal-Contract — PROP-01, PROP-02, PROP-03, PROP-04
- `docs/PRD.md` §6.1 (data flow, step 4 = advance-to-proposal), §6.2 (Engagement Record shape), §7.2 (Proposal-Contract Agent tools + output)

### Phase 3 foundation (this branch is stacked on it)
- `backend/api.py` — `/capture`, `/engagements/{id}`, `get_store`, `map_bedrock_error`/`BedrockUnavailableError`, the VERBATIM typed-merge and 503 fail-fast patterns to mirror for `/advance`
- `backend/agents/triage_runner.py` — the `TriageRunner` seam (`get_triage_runner`, deterministic vs `_supervisor_*` paths, env flag) to mirror as `ProposalRunner`
- `backend/agents/supervisor.py` — `build_supervisor` + `extract_triage_result` (typed toolResult extraction) to mirror for the proposal specialist
- `backend/agents/gig_triage_agent.py`, `backend/tools/placeholder_triage.py` — the specialist-Agent + dual-use `@tool` pattern to mirror
- `backend/models/engagement_record.py` — `ProposalSlice`/`ContractSlice`/`EngagementRecord` this phase populates/enriches
- `backend/store/engagement_store.py`, `backend/store/file_engagement_store.py` — `get`/`save` used by `/advance` (sole-writer)
- `backend/tests/test_single_writer.py` — the AST guard the new agents/tools must not trip

### Verified stack/architecture
- `.planning/research/STACK.md` §2 (agents-as-tools), §3 (`@tool` typed results), §4 (BedrockModel), §5 (FastAPI/Pydantic)
- `.planning/research/ARCHITECTURE.md` — FastAPI-as-sole-writer, specialist typed-JSON merge
- `.planning/research/PITFALLS.md` — structured-output escalation-field trap (Pitfall 3), Supervisor re-authoring anti-pattern, Bedrock cred traps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EngagementRecord` + `ProposalSlice`/`ContractSlice` (Phase 1) — already present as minimal
  stubs matching PRD §6.2; this phase enriches and populates them.
- `TriageRunner` seam + `get_triage_runner` (Phase 3) — the exact DI-seam pattern to copy for `ProposalRunner`.
- `map_bedrock_error` / `BedrockUnavailableError` (Phase 3, `api.py`) — reuse directly for `/advance`'s 503 mapping.
- `extract_triage_result` (Phase 3, `supervisor.py`) — the typed toolResult-block extraction to mirror for the proposal specialist's live path.
- `placeholder_triage.py` (Phase 3) — the dual-use `@tool` (plain-Python + Agent-registered) template.
- `EngagementStore.save()` (Phase 1) — already exists; `/advance` uses `get()` → merge → `save()` (no new store method needed).

### Established Patterns
- **Single-writer rule** (`test_single_writer.py`) — only `backend/api.py` imports the store; the new agents/tools MUST NOT import it.
- **Deterministic seam + env-selected live path** — default deterministic, `*_BACKEND` env selects the supervisor/live path (Phase 3 `TRIAGE_BACKEND` → Phase 5 `PROPOSAL_BACKEND`).
- **Bedrock fail-fast** — never leak credentials or a raw AWS `Message`; map to a static, typed 503.
- **VERBATIM typed merge** — FastAPI reads the specialist's typed object from a structured channel, never the Supervisor's prose.

### Integration Points
- New endpoint `POST /engagements/{id}/advance` added to `backend/api.py` alongside `/capture` and `/engagements/{id}`.
- The `ProposalRunner` seam is exactly what the live Proposal-Contract Agent drops into (and what Phase 6 extends toward ORC-01).

</code_context>

<specifics>
## Specific Ideas

- SC3 (mutual exclusivity) is the structural anti-guessing guard — the happy path and the
  escalation path must be two outcomes of ONE schema, provable by a test that asserts a
  populated contract and `needs_human_input=true` never co-occur.
- The ambiguous fixture must be chosen so the deterministic `check_scope_clarity` gate
  fires (e.g. missing budget AND/OR missing deliverables), making SC2 deterministic offline.

</specifics>

<deferred>
## Deferred Ideas

- Full three-agent Supervisor (ORC-01) — Phase 6.
- `stage="ops"` advancing + formal API-03 completion — Phase 6.
- Ops specialist, scope-creep/invoice tooling, Stage 2–3 fixture set (DEMO-01) — Phase 6.
- LLM-authored proposal/contract prose quality — the live path exists behind the seam; the demo runs deterministic.

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-Proposal-Contract Agent + /advance (stage="proposal")*
*Context gathered: 2026-09-05*
