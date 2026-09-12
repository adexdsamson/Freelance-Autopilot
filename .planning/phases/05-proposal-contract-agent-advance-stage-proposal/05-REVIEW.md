---
phase: 05-proposal-contract-agent-advance-stage-proposal
reviewed: 2026-09-05T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - backend/models/engagement_record.py
  - backend/tools/check_scope_clarity.py
  - backend/tools/draft_proposal.py
  - backend/tools/draft_contract.py
  - backend/agents/proposal_runner.py
  - backend/agents/proposal_contract_agent.py
  - backend/agents/supervisor.py
  - backend/api.py
  - backend/tests/test_proposal_runner.py
  - backend/tests/test_advance_endpoint.py
  - backend/tests/test_advance_bedrock_failfast.py
  - backend/tests/test_proposal_supervisor_wiring.py
findings:
  blocker: 1
  warning: 3
  suggestion: 2
  total: 6
status: resolved
fixed_at: 2026-09-05T00:00:00Z
fix_commits:
  CR-01: b417557
  WR-01: 046b564
  SG-02: 046b564
  WR-02: fc2377a
  WR-03: fc2377a
  SG-01: b25dd84
---

# Phase 5: Code Review Report

**Reviewed:** 2026-09-05
**Depth:** standard
**Files Reviewed:** 12 (11 source/agent/tool files + 4 test files, one counted above the diff's own file list; see `files_reviewed_list` for exact scope)
**Status:** issues

## Summary

Reviewed the full Phase 5 diff (`37432db..HEAD -- backend/`): the enriched `EngagementRecord`
schema (`PaymentMilestone`, `ProposalContractResult` + mutual-exclusivity validator), the three
deterministic `@tool` functions, the `ProposalRunner` seam, the `proposal_contract_agent` +
`build_proposal_supervisor`/`extract_proposal_result` live-path wiring, and the new
`POST /engagements/{id}/advance` endpoint, plus all four new test files. The full suite (76
tests) passes offline with placeholder credentials.

The deterministic-first design, the sole-writer discipline (verified: no `agents/`/`tools/`
module imports the store), the stage-scoped supervisor (verified: `build_supervisor` is
byte-for-byte unmodified in the diff), and the credential-free 503 fail-fast are all correctly
implemented and match the locked decisions (D-01 through D-07).

However, direct testing (reproduced below, not merely inferred) surfaced one genuine violation
of the phase's own headline guarantee (SC3, mutual exclusivity) at the persisted-record level —
the schema-level validator is correct, but `api.py`'s merge logic does not clear a stale
`contract` slice when a later `/advance` call escalates, so the persisted record (and the HTTP
response) can carry `needs_human_input=true` alongside a fully populated contract. Three
further correctness/quality issues were found in the deterministic tools (a payment-schedule
rounding drift that silently miscalculates totals for realistic non-round budgets, and a keyword
heuristic with a demonstrated false-positive substring match that can suppress a legitimate
escalation).

## Critical Issues

### CR-01: `/advance`'s merge does not clear `record.contract` on escalation, breaking SC3 at the persisted-record level

**File:** `backend/api.py:185-195`
**Issue:** The merge logic is:
```python
record.proposal = ProposalSlice(
    text=result.proposal_text,
    needs_human_input=result.needs_human_input,
    question=result.question,
)
if not result.needs_human_input:
    record.contract = ContractSlice(
        text=result.contract_text,
        payment_schedule=result.payment_schedule,
    )
store.save(record)
```
`record.proposal` is always overwritten, but `record.contract` is only ever *written* on the
happy path — there is no `else: record.contract = None` (or equivalent) branch to clear a
previously-populated contract when a later call escalates. `ProposalContractResult`'s
`model_validator` correctly prevents a *single* result object from carrying both a populated
contract and `needs_human_input=True` (SC3 is genuinely enforced at the schema level — verified
by `test_exclusivity_rejects_both_populated`), but SC3's intent — "no `/advance` response
contains both a fully populated contract and `needs_human_input=true`" (05-CONTEXT.md D-01,
05-01-PLAN.md `must_haves.prohibitions`) — is a statement about the **persisted record /
endpoint response**, not just the transient result object, and that guarantee does not hold once
an engagement is advanced more than once with differing outcomes.

This is directly reachable on the live path (`PROPOSAL_BACKEND=supervisor`), which is a real,
shipped code path (not hypothetical) selected by an env var — an LLM-backed specialist can
plausibly draft successfully on one invocation and escalate on a retry/re-advance of the same
engagement (non-deterministic by nature), leaving the previous contract on disk while the new
response claims `needs_human_input=true`. It is not reachable via the deterministic default
today only because the deterministic runner is a pure function of unchanging job fields — but
nothing in the code enforces that invariant, and this is exactly the kind of double-write bug
`test_advance_endpoint.py` does not cover (both existing endpoint tests each advance an
engagement exactly once).

**Reproduced directly** (not merely inferred) by advancing the same engagement twice — first
via the real deterministic happy path, then via an injected runner returning an escalation
result for the same `job`:
```
first advance contract text present: True
second advance needs_human_input: True
second advance contract (should arguably be null but is): {'text': 'Statement of Work: t...', 'payment_schedule': [...]}
```
The second response/persisted-record has `proposal.needs_human_input == True` **and** a fully
populated `contract` — the exact state SC3 is meant to structurally forbid.

**Fix:**
```python
record.proposal = ProposalSlice(
    text=result.proposal_text,
    needs_human_input=result.needs_human_input,
    question=result.question,
)
if result.needs_human_input:
    record.contract = None
else:
    record.contract = ContractSlice(
        text=result.contract_text,
        payment_schedule=result.payment_schedule,
    )
store.save(record)
```

## Warnings

### WR-01: `draft_contract`'s independently-rounded payment-schedule amounts can silently not sum to the budget

**File:** `backend/tools/draft_contract.py:44-58`
**Issue:** Each milestone amount is computed as `round(budget * fraction, 2)` independently
(0.3 / 0.5 / 0.2). For budgets that don't happen to produce "nice" fractional cents, the three
independently-rounded amounts can sum to a different total than `budget`. Reproduced directly:
```
budget=999.99  -> milestones sum to 1000.00   (off by +$0.01)
budget=333.33  -> milestones sum to 333.33    (coincidentally exact)
budget=2000.0  -> milestones sum to 2000.00   (coincidentally exact)
```
The only automated coverage of this
(`test_draft_contract_payment_schedule_items_have_required_keys_and_sum_to_budget`,
`backend/tests/test_proposal_runner.py:60-66`) uses `budget=2000.0`, a value where the rounding
happens to cancel out, so the test passes while masking the underlying bug. Since PROP-03/D-06
frame this as a "structured (typed) payment schedule" a client is meant to trust as the contract
of record, a milestone total that silently diverges from the quoted budget by a cent is a real
correctness defect in a financial document, not merely cosmetic.
**Fix:** Compute the first two milestones by rounding and derive the last as the remainder so
the schedule is guaranteed to sum exactly to `budget`:
```python
first = round(budget * 0.3, 2)
second = round(budget * 0.5, 2)
third = round(budget - first - second, 2)
```

### WR-02: `check_scope_clarity`'s `"by "` timeline marker produces a demonstrated false-positive that suppresses a legitimate escalation

**File:** `backend/tools/check_scope_clarity.py:29,45`
**Issue:** `TIMELINE_MARKERS` includes the bare substring `"by "` (a literal space after `by`),
matched via unanchored `marker in lowered`. This matches inside unrelated words that merely
contain the letters `b`, `y`, and a following space — e.g. `"nearby "`, `"standby "`,
`"thereby "`. Reproduced directly: a description with genuinely no timeline signal —
`"Looking for a nearby freelancer to build a small marketing site with three deliverable phases
and milestone reviews."` — is judged `{"clear": True, "question": None}` purely because
`"nearby "` contains `"by "`. This means `check_scope_clarity` (PROP-04's structural
anti-guessing gate) can fail to escalate on a job whose timeline is genuinely ambiguous,
directly undermining SC2's intent ("escalate on ambiguous scope instead of guessing"). The
module docstring flags the keyword lists as an `[ASSUMED] design-choice`, but this specific
marker is unusually failure-prone because it lacks any word boundary.
**Fix:** Require a preceding word boundary/space before `by`, or drop the standalone `"by "`
marker in favor of more specific phrases (e.g. `"by friday"`, `"by end of"`) — or use a regex
with `\bby\b` anchored to word boundaries instead of raw substring containment.

### WR-03: No defensive validation in `draft_contract`/`draft_proposal` for non-positive `budget`

**File:** `backend/tools/draft_contract.py:19-58`, `backend/tools/draft_proposal.py:18-39`
**Issue:** Neither tool validates that `budget > 0`. `check_scope_clarity` only checks
`budget is None`, so `budget=0.0` or a negative budget is treated as "provided." In the current
deterministic-default flow this is not reachable end-to-end because the upstream triage gate
(`placeholder_kill_switch_check`, `BUDGET_FLOOR = 100.0`) skips any non-`None` budget below
100.0 before an engagement can reach `apply` verdict (a precondition for `/advance`) — reproduced
directly: `draft_contract(..., budget=-1000.0)` happily returns negative payment-schedule
amounts (`-300.0`, `-500.0`, `-200.0`), which would only be reachable if a live specialist agent
called the tool directly with an out-of-band value, or if the triage budget floor is ever
relaxed/removed by a future phase. Low severity today given the guard, but the tools themselves
have no defense-in-depth.
**Fix:** Add an explicit guard in `check_scope_clarity` (or `draft_contract`) treating
`budget <= 0` the same as `budget is None` (missing budget), so the gate's purpose ("flags
missing budget") is not solely dependent on an upstream, differently-scoped rule.

## Suggestions

### SG-01: `ProposalContractResult`'s validator does not forbid a stray `question` alongside a fully-populated happy path

**File:** `backend/models/engagement_record.py:72-93`
**Issue:** The `else` branch (happy path) only checks `proposal_text`/`contract_text`/
`payment_schedule` are all populated; it never asserts `question is None`. A result with
`needs_human_input=False`, all three happy fields populated, AND a non-empty `question` passes
validation. `api.py` would then merge that stray `question` into `record.proposal.question`
alongside `needs_human_input=False` and a populated contract — a minor but avoidable data-shape
inconsistency, most likely to surface via the live path if the LLM specialist doesn't perfectly
follow its system prompt.
**Fix:** Add `if self.question: raise ValueError(...)` to the `else` branch, or explicitly clear
`question` in the happy-path model construction sites.

### SG-02: DEMO-02 rounding assertion in the payment-schedule test is a false-confidence test (see WR-01)

**File:** `backend/tests/test_proposal_runner.py:60-66`
**Issue:** `test_draft_contract_payment_schedule_items_have_required_keys_and_sum_to_budget`
only exercises `budget=2000.0`, a value for which independent per-milestone rounding happens to
cancel out (see WR-01). The test name promises a general "sum to budget" guarantee that the
implementation does not actually provide for arbitrary budgets.
**Fix:** Parametrize the test with a non-round budget (e.g. `999.99`, `333.33`) once WR-01 is
fixed, to actually prove the summation guarantee rather than coincidentally satisfy it.

---

## Disposition

All 6 findings fixed on branch `gsd/phase-05-proposal-contract-agent-advance-stage-proposal`.
Full suite green: 84 passed, 0 failures (76 original + 8 new/parametrized regression tests).

- **CR-01** (fixed, commit `b417557`): `api.py`'s `/advance` merge now sets
  `record.contract = None` on the escalation branch. Added
  `test_advance_re_advance_escalation_clears_stale_contract` (happy-then-escalation
  re-advance via an overridden runner; asserts both the response and the persisted
  record clear `contract`).
- **WR-01** (fixed, commit `046b564`): `draft_contract` now derives the final milestone
  as the remainder (`budget - first - second`) so the schedule sums exactly to budget.
- **WR-02** (fixed, commit `fc2377a`): `check_scope_clarity`'s timeline markers are now
  matched via a word-boundary-anchored regex (`_contains_marker`), so `"nearby "` no
  longer false-positives the `"by "` marker while a real `"by <date>"` still matches.
- **WR-03** (fixed, commit `fc2377a`): `check_scope_clarity` now treats a non-positive
  (`<= 0`) budget the same as a missing budget.
- **SG-01** (fixed, commit `b25dd84`): `ProposalContractResult`'s validator now rejects
  a happy-path result (`needs_human_input=False`) carrying a non-None `question`.
- **SG-02** (fixed, commit `046b564`): the payment-schedule "sum to budget" test is now
  parametrized with `999.99` and `333.33` (in addition to `2000.0`), proving the
  summation guarantee instead of coincidentally satisfying it.

_Reviewed: 2026-09-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Fixed: 2026-09-05_
_Fixer: Claude (gsd-code-fixer)_
