# Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning
**Mode:** Auto-generated (`--only 6` autonomous run, `--auto` discuss; decisions grounded in research, PRD §7.3/§10, and the Phase-3/5 seam/placeholder/sole-writer precedent)

<domain>
## Phase Boundary

This phase completes the multi-agent core: it (a) unifies the Supervisor so its tools list
holds **all three** specialist agents (Gig Triage, Proposal-Contract, **Ops**) — ORC-01;
(b) builds the Stage 3 **Ops specialist** that flags scope creep and overdue invoices and
drafts a client-ready status update against **deterministic fixtures**; (c) extends
`POST /engagements/{id}/advance` to route `stage="ops"` as well as `stage="proposal"` —
completing API-03; and (d) ships the Stage 2–3 fixture set (DEMO-01). Delivers **ORC-01,
API-03, OPS-01, OPS-02, OPS-03, OPS-04, DEMO-01**.

**Stacked on `gsd/phase-05`.** This is an `--only 6` run; the branch
`gsd/phase-06-ops-agent-fixtures-full-supervisor-wiring` is forked from `gsd/phase-05`
(carries the Engagement Record + store, the Gig Triage specialist + `/capture` (Phase 3),
and the Proposal-Contract specialist + `/advance` proposal stage (Phase 5)). ORC-01 needs
both existing specialists present, which is exactly why Phase 6 depends on Phase 5.

**Out of scope (belongs to other phases/engineers):**
- The Chrome MV3 extension (Phase 4) — separate track.
- The real Gig Triage tools (`extract_job_fields`/`kill_switch_check`/`llm_scorecard`, TRI-01..04) — Phase 2, behind the existing triage seam; the placeholder specialist stands in for ORC-01 wiring.
- README, demo script, architecture diagram, OSI license, deterministic end-to-end demo run (DEMO-02..05) — Phase 7.
- AgentCore Memory/Runtime — Phase 8 (cut-first).

</domain>

<decisions>
## Implementation Decisions

### ORC-01 — unified three-specialist Supervisor (SC1)
- **D-01:** Add a **new** `build_full_supervisor()` that registers **all three** specialist
  agents — `gig_triage_agent`, `proposal_contract_agent`, `ops_agent` — as agents-as-tools
  on ONE Supervisor, so its tools list contains all three and a run shows **four distinct,
  independently traceable Agent invocations** (SC1). Keep the Phase-3/5 stage-scoped
  `build_supervisor`/`build_proposal_supervisor` intact (do not delete them). Because a
  3-tool supervisor can emit multiple toolResult blocks, the live-path extraction must
  **disambiguate by tool name** (`toolUse.name` → the matching specialist's `toolResult`
  json), generalizing the Phase-3/5 first-json-block scan — this is the toolUseId↔name
  disambiguation Phase 5 deferred. — **Reversibility:** costly — this is the "genuine
  multi-agent orchestration visible in code" the judges score; the extraction contract is
  load-bearing.

### Ops specialist + tools (PRD §7.3), deterministic bodies, dual-use, no store import
- **D-02:** Build the three PRD §7.3 tools as the ONE source of truth for their rules,
  `@tool`-decorated and dual-use (plain Python for the deterministic path + registered on
  the Ops Agent for the live path), mirroring the Phase-3/5 tool pattern; none import the
  store (single-writer, REC-03):
  - `check_scope_creep` — compares incoming (fixture) client-thread messages against the
    signed SOW's enumerable deliverables and flags creep (OPS-01).
  - `check_invoice_status` — flags milestones overdue against the payment schedule (OPS-02).
  - `draft_status_update` — a client-ready status summary reflecting whatever flags are
    currently active (OPS-03, SC4).
  A distinct `build_ops_agent()` specialist Agent wraps these for the live path.

### OpsRunner seam (mirrors TriageRunner / ProposalRunner)
- **D-03:** Add an `OpsRunner` DI seam (`get_ops_runner`, `_deterministic_ops_runner`,
  `_supervisor_ops_runner`, `OPS_BACKEND` env) exactly like Phase 3/5. Deterministic is the
  **default** (offline, demo-repeatable); `OPS_BACKEND=supervisor` selects the live path.
  The runner takes the record (its contract SOW) + the loaded fixture thread + payment
  schedule → a typed ops result (status update + escalation cards). — **Reversibility:**
  reversible — body change behind a stable interface.

### Fixtures (DEMO-01, PRD §10) — deterministic, with clean vs creep variants
- **D-04:** Ship `backend/fixtures/`: `sample_client_thread.json` (a thread containing a
  **deliberate scope-creep message**) plus a **clean variant** (no creep);
  `sample_payment_schedule.json` (**one overdue milestone**) plus a **clean variant** (none
  overdue); and `sample_upwork_jobs.json` (5–8 mixed-fit postings). A **variant selector**
  (e.g. an `/advance` `fixture=creep|clean` param, or a loader key) drives SC2 (creep → 2
  cards) vs SC3 (clean → 0 cards). Fixtures are pure data (no store import). — **Reversibility:**
  reversible.

### `/advance` stage=ops — completing API-03 (SC5), FastAPI sole-writer (REC-03)
- **D-05:** Extend the existing `/advance` handler's stage guard with the already-stubbed
  `elif stage == "ops":` branch: load the record, guard the ops precondition (a
  contract/SOW must exist — otherwise a 4xx), run the specialist via the `OpsRunner` DI
  seam, merge the typed ops result **VERBATIM** into the `ops` slice, persist via
  `store.save()`, return the updated record. Reuse `map_bedrock_error` → credential-free
  **503**. After this, `/advance` routes+completes **both** `proposal` and `ops` (API-03).
  — **Reversibility:** costly — the endpoint's stage-routing + status-code contract is what
  clients and the demo build on.

### Escalation cards (OPS-04) — distinct + conditional
- **D-06:** Each scope-creep flag, each invoice flag, and any judgment-needed status is a
  **distinct escalation card** in the ops output (OPS-04). The checks are **conditional**,
  not hardcoded: the clean fixture variant yields **zero** cards (SC3), the creep+overdue
  variant yields **exactly two** (SC2). Represent cards as a typed model so counts are
  machine-checkable.

### Ops slice typing
- **D-07:** `OpsSlice` currently holds `status_updates`/`scope_creep_flags`/`invoice_flags`
  as `list[dict]`; tighten to typed cards where it makes the SC2/SC3 assertions cleaner.
  Enriching the Phase-1 stub is in scope. — **Reversibility:** costly — persisted record shape.

### Credential-less test strategy (sandbox has placeholder AWS creds) — same precedent as Phase 3/5
- **D-08:** Offline tests (no creds) MUST pass and verify: (a) `build_full_supervisor()`
  constructs offline with all three specialist tools registered and four distinct Agent
  instances (SC1, ORC-01) — construction-only, no network; (b) the creep+overdue fixture →
  exactly two distinct escalation cards (SC2); (c) the clean fixture → zero cards (SC3);
  (d) `draft_status_update` reflects the active flags (SC4); (e) `/advance` routes+completes
  **both** `proposal` and `ops` stages, returning the updated record each time (SC5); (f)
  the ops slice is merged FastAPI-only (REC-03); (g) `/advance` ops fails fast + readably
  (503, never a raw 500) when the live path raises. The **live four-agent Bedrock trace**
  (`OPS_BACKEND=supervisor` / the unified supervisor) is documented **manual** verification,
  exactly as in Phases 1/3/5.

### Claude's Discretion
- Module layout (`backend/agents/ops_agent.py`, `backend/agents/ops_runner.py`,
  `backend/tools/{check_scope_creep,check_invoice_status,draft_status_update}.py` per PRD §12,
  vs consolidating), the exact typed card/result model names, the precise ops-precondition
  4xx code, the fixture-variant selector mechanism, the deterministic creep/overdue rules,
  and whether `build_full_supervisor` lives in `supervisor.py` — all at Claude's discretion,
  consistent with the Phase 3/5 idioms.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project specs
- `.planning/PROJECT.md` — scope, constraints, key decisions
- `.planning/REQUIREMENTS.md` §Orchestration (ORC-01), §Capture API (API-03), §Ops (OPS-01..04), §Fixtures/Demo (DEMO-01)
- `docs/PRD.md` §6.1 (data flow steps 5–6 = time-jump + Ops), §6.2 (Engagement Record `ops` slice shape), §7.3 (Ops Agent tools + output), §10 (mocked data / fixtures)

### Phase 3 + Phase 5 foundation (this branch is stacked on both)
- `backend/agents/supervisor.py` — `build_supervisor`/`build_proposal_supervisor` + `extract_triage_result`/`extract_proposal_result`; the agents-as-tools + toolResult-extraction pattern `build_full_supervisor` generalizes (by tool name) for ORC-01
- `backend/agents/proposal_runner.py`, `backend/agents/triage_runner.py` — the runner-seam pattern to mirror as `OpsRunner`
- `backend/agents/proposal_contract_agent.py`, `backend/agents/gig_triage_agent.py` — specialist-Agent builders to register into the unified supervisor
- `backend/tools/{check_scope_clarity,draft_proposal,draft_contract,placeholder_triage}.py` — dual-use `@tool` pattern to mirror for the ops tools
- `backend/api.py` — `/advance` handler with the stubbed `elif stage == "ops"` seam, `map_bedrock_error`, `get_store`, the VERBATIM merge + 503 fail-fast to extend
- `backend/models/engagement_record.py` — `OpsSlice` (this phase enriches) + `EngagementRecord`
- `backend/store/engagement_store.py` — `get`/`save` used by `/advance` (sole-writer)
- `backend/tests/test_single_writer.py` — the AST guard the new ops agents/tools must not trip

### Verified stack/architecture
- `.planning/research/STACK.md` §2 (agents-as-tools), §3 (`@tool` typed results), §4 (BedrockModel), §5 (FastAPI/Pydantic)
- `.planning/research/ARCHITECTURE.md` — FastAPI-as-sole-writer, specialist typed-JSON merge
- `.planning/research/PITFALLS.md` — Supervisor re-authoring anti-pattern, multi-tool disambiguation, Bedrock cred traps

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_supervisor`/`build_proposal_supervisor` + `extract_triage_result`/`extract_proposal_result` (supervisor.py) — the exact shape `build_full_supervisor` + a name-disambiguated extractor generalize.
- `TriageRunner`/`ProposalRunner` seams — copy for `OpsRunner`/`get_ops_runner` + `OPS_BACKEND`.
- `map_bedrock_error`/`BedrockUnavailableError` (api.py) — reuse for the ops-stage 503.
- `/advance` handler already has the `elif stage == "ops"` seam comment (Phase 5 left it deliberately) — extend, don't rewrite.
- `OpsSlice` (engagement_record.py) — already present as a stub (status_updates/scope_creep_flags/invoice_flags); enrich to typed cards.
- `EngagementStore.save()` — `/advance` ops uses `get()` → merge → `save()`.
- The dual-use `@tool` pattern (placeholder_triage.py, draft_*.py) — copy for the three ops tools.

### Established Patterns
- **Single-writer rule** (`test_single_writer.py`) — only `backend/api.py` imports the store; new ops agents/tools MUST NOT.
- **Deterministic default + env-selected live path** — `OPS_BACKEND` unset → deterministic; `=supervisor` → live (unified supervisor).
- **VERBATIM typed merge** — FastAPI reads the specialist's typed object from a structured channel, never the Supervisor's prose.
- **Bedrock fail-fast** — never leak credentials/AWS Message; map to a static, typed 503.
- **Manual live trace** — the multi-agent Bedrock run is documented manual verification.

### Integration Points
- Unified supervisor (`build_full_supervisor`) is the ORC-01 artifact + the live path for all stages.
- `/advance` gains the ops branch; the ops slice is the last empty slice in the Engagement Record.
- Fixtures under `backend/fixtures/` feed the ops stage (and seed the Phase 7 demo).

</code_context>

<specifics>
## Specific Ideas

- SC1 (four traceable agents) is the anti-"single wrapped call" guard for the whole project — provable offline by asserting the unified supervisor's `tool_names` contains all three specialist tools and that four distinct `Agent` instances exist.
- SC3 (clean variant → 0 cards) is the anti-"hardcoded flags" guard — the same code path must yield zero cards on the clean fixture and two on the creep+overdue fixture, so the fixtures must be chosen to make both deterministic.
- API-03 is only complete when BOTH `proposal` and `ops` stages route+complete through `/advance` (SC5) — keep a test that exercises the full capture→proposal→ops progression on one engagement.

</specifics>

<deferred>
## Deferred Ideas

- Chrome MV3 extension (CAP-01..03) — Phase 4.
- Real Gig Triage tools (TRI-01..04) — Phase 2, behind the existing seam.
- Deterministic end-to-end demo run, README, demo script, architecture diagram, OSI license (DEMO-02..05) — Phase 7.
- AgentCore Memory/Runtime (DEPLOY-01/02) — Phase 8 (cut-first).

None else — discussion stayed within phase scope.

</deferred>

---

*Phase: 6-Ops Agent, Fixtures & Full Supervisor Wiring*
*Context gathered: 2026-09-08*
