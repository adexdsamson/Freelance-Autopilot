# Phase 2: Gig Triage Agent (standalone) - Context

**Gathered:** 2026-09-02
**Status:** Executed

<domain>
## Phase Boundary

This phase builds the Stage 1 specialist: raw pasted job text in, a
`{verdict, score, reasoning, extracted_fields}` triage result out. It delivers
TRI-01, TRI-02, TRI-03, TRI-04. It does NOT build the Supervisor, any FastAPI
endpoint, or the Chrome extension - the specialist is exercised standalone via
`scripts/run_triage.py` and unit tests only. Phase 3 wraps `run_triage` in an
`@tool` for the Supervisor and adds `/capture`.

</domain>

<decisions>
## Implementation Decisions

Built on Phase 1's locked decisions (D-01..D-08). New to this phase:

### Orchestration inside the specialist
- **D-09:** The specialist sequences its three tools in a **fixed Python order**
  (extract -> gate -> scorecard) rather than registering them on an `Agent` and
  letting a model choose. Three reasons: (a) a model that can decline to call
  `kill_switch_check` turns a hard disqualification into an advisory one;
  (b) DEMO-02 requires three fixture runs with identical verdicts, and
  model-chosen tool ordering is exactly that variance; (c) a rejected posting
  costs zero tokens. - **Reversibility:** reversible - the three tools are
  already `@tool`-decorated, so registering them on an `Agent` later is additive.
- **D-10:** The LLM judgement still runs through a real Strands `Agent` +
  `BedrockModel` inside `llm_scorecard`, so Phase 3's "two distinct Agent
  invocations" criterion is satisfied by a genuine second invocation, not a
  wrapper.

### Determinism
- **D-11:** The composite 0-100 score is computed **in code** from the model's
  three sub-scores (weights in `triage_config.py`), never asked of the model.
  `ScorecardJudgment` deliberately has no `score` field. Identical sub-scores
  therefore always produce an identical total.
- **D-12:** `BedrockModel` is constructed with `temperature=0.0`. Necessary for
  DEMO-02 but not sufficient on its own, which is the other reason for D-11.

### Gate policy
- **D-13:** Two-tier client-history ladder. Below `MIN_*` is a hard rejection;
  between `MIN_*` and `HEALTHY_*` is a **flag** passed into the scorecard prompt
  as a concern the model must weigh. This keeps the gate from silently killing
  viable gigs while still making thin clients visible.
- **D-14:** Missing metadata is always a flag, never a pass and never a
  rejection. An unstated hire rate must not read as either a perfect one or a
  0% one.
- **D-15:** `budget_type` (`fixed`/`hourly`/`unknown`) is tracked on
  `ExtractedJobFields` even though PRD 6.2's `JobSlice` has no such field,
  because a budget floor cannot be applied correctly without it. It stays on
  the triage side of the boundary.

### Schema strictness
- **D-16:** `extra="forbid"` on every contract model (`TriageResult`,
  `ExtractedJobFields`, `ClientStats`, `KillSwitchResult`) - this is what makes
  TRI-04's "no escalation fields" structural rather than conventional. It is
  deliberately NOT set on `ScorecardJudgment`, the one model an LLM fills, so a
  stray provider key cannot crash a recorded demo; its ge/le bounds still reject
  bad numbers.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/REQUIREMENTS.md` Gig Triage - TRI-01..TRI-04
- `.planning/ROADMAP.md` Phase 2 - the four success criteria
- `.planning/phases/01-.../01-CONTEXT.md` - D-01..D-08, still binding
- `backend/models/engagement_record.py` - `JobSlice`/`TriageSlice`, the shapes
  Phase 3's merge targets
- `backend/tests/test_single_writer.py` - the REC-03/D-05 boundary this phase's
  new `agents/` and `tools/` modules must not violate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1's `@tool` shape, verified against the pinned `strands-agents==1.54.0`:
  a decorated function stays directly callable from Python and exposes
  `.tool_name` (re-confirmed by probe before building on it).
- Phase 1's fail-fast error handling in `scripts/smoke_test_bedrock_connectivity.py`
  - the same "type name only, never the raw AWS message" rule (T-01-02) is
  carried into `scripts/run_triage.py`.
- `Agent`/`BedrockModel` imported at module level so tests can monkeypatch them,
  the pattern `tests/test_bedrock_smoke.py` established.

### Integration Points
- `run_triage(raw_text) -> TriageResult` is the single callable Phase 3 wraps in
  an `@tool` for the Supervisor.
- `ExtractedJobFields` is field-compatible with `JobSlice`, and `TriageResult`'s
  `verdict`/`score`/`reasoning` are exactly `TriageSlice`'s fields, so Phase 3's
  FastAPI merge is a field copy, not a translation.

</code_context>

<specifics>
## Specific Ideas

- The gate must be provably LLM-free. Implemented as an autouse pytest fixture
  that replaces `Agent`/`BedrockModel` with something that raises on
  construction, so an accidental model call fails the suite rather than quietly
  costing tokens and requiring credentials in CI.
- Red-flag entries are multi-word phrases, not single words: "equity", "test"
  and "sample" all false-positive constantly in legitimate postings.

</specifics>

<deferred>
## Deferred Ideas

- Registering the three tools on a model-driven `Agent` (see D-09) - additive
  later if a phase ever needs model-chosen ordering.
- URL-based capture. TRI-01 mentions "text/URL"; only paste is implemented,
  matching PROJECT.md's no-scraping compliance constraint (CAP-01, Phase 4).
- Per-freelancer configurable thresholds - `triage_config.py` is module-level
  constants; making them per-user is a v2 concern.

</deferred>

---

*Phase: 2-Gig Triage Agent (standalone)*
