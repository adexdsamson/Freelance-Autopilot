---
phase: 06-ops-agent-fixtures-full-supervisor-wiring
reviewed: 2026-09-08T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - backend/agents/ops_agent.py
  - backend/agents/ops_runner.py
  - backend/agents/supervisor.py
  - backend/api.py
  - backend/fixtures/__init__.py
  - backend/fixtures/loader.py
  - backend/fixtures/sample_client_thread.json
  - backend/fixtures/sample_client_thread_clean.json
  - backend/fixtures/sample_payment_schedule.json
  - backend/fixtures/sample_payment_schedule_clean.json
  - backend/fixtures/sample_upwork_jobs.json
  - backend/models/engagement_record.py
  - backend/tools/check_scope_creep.py
  - backend/tools/check_invoice_status.py
  - backend/tools/draft_status_update.py
  - backend/tests/test_advance_bedrock_failfast.py
  - backend/tests/test_advance_endpoint.py
  - backend/tests/test_fixtures_loader.py
  - backend/tests/test_full_supervisor_wiring.py
  - backend/tests/test_ops_runner.py
  - backend/tests/test_ops_tools.py
findings:
  blocker: 1
  high: 0
  medium: 2
  low: 3
  total: 6
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-09-08
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

The deterministic path (the one exercised by the full automated test suite — 118 tests,
all green) is solid: `check_scope_creep`/`check_invoice_status`/`draft_status_update` are
genuinely pure, the fixture variant selector is data-driven (not hardcoded), `OpsSlice`'s
escalation-card counts trace correctly through to SC2 (=2)/SC3 (=0), the REC-03 sole-writer
rule holds for every file in `backend/agents/` and `backend/tools/` (confirmed by
`test_single_writer.py`'s AST scan and by manual inspection), the `fixture` query param is
a closed `Literal["creep","clean"]` that structurally forecloses path traversal, and the
ops-branch 503 reuses `map_bedrock_error` verbatim with no credential/Message leakage.

The one genuine defect (BLOCKER below) is in the **live path**
(`OPS_BACKEND=supervisor` / `build_full_supervisor()`), which per D-08 is
manual-verification-only and therefore invisible to the automated suite: the Ops
specialist's registered tools require real client-thread messages, a real ops-shaped
payment schedule, and an explicit reference date as arguments, but `_supervisor_ops_runner`
never loads the fixture data or supplies a reference date into the prompt — the docstring's
claim that "both paths call the SAME three @tool functions, so the two paths can never
drift apart" is false for the live path as currently wired; it cannot produce a
fixture-grounded result at all. Since this is exactly the "genuine multi-agent
orchestration visible in code" mechanism judges are expected to trace (ORC-01/D-01), this
is flagged BLOCKER despite sitting outside the automated test net.

The remaining findings are quality/robustness items (duplicated tool-result-scan logic,
a test-coverage gap for the REC-03 guard on `fixtures/`, a naive heuristic, and a
minor field-semantics mismatch) — none block the demo path but are worth tightening.

## Blocker Issues

### BL-01: Live Ops path (`OPS_BACKEND=supervisor`) cannot produce a fixture-grounded result — the dual-use "never drift" guarantee is broken

**Disposition: FIXED.** `_supervisor_ops_runner` in `backend/agents/ops_runner.py`
now loads `thread_messages`/`payment_schedule` via `load_client_thread`/
`load_payment_schedule` and computes `reference_date = date.today().isoformat()`
at the call site (mirroring `_deterministic_ops_runner`), and inlines all three
into the supervisor prompt alongside `contract.model_dump_json()`. See
06-REVIEW-FIX.md.

**File:** `backend/agents/ops_runner.py:72-89` (`_supervisor_ops_runner`), `backend/agents/ops_agent.py:41-56` (`build_ops_agent`), `backend/tools/check_scope_creep.py:41`, `backend/tools/check_invoice_status.py:33`

**Issue:**
`ops_agent.py`'s module docstring and `ops_runner.py`'s docstring both assert that the
deterministic and live paths "call the SAME three @tool functions, so the two paths can
never drift apart" (D-02). That is true only for the *deterministic* path
(`_deterministic_ops_runner`), which explicitly does:

```python
thread_messages = load_client_thread(fixture)
payment_schedule = load_payment_schedule(fixture)
...
creep = check_scope_creep(contract.text or "", thread_messages)
invoices = check_invoice_status(payment_schedule, date.today().isoformat())
```

`check_scope_creep(contract_text: str, thread_messages: list[str])` and
`check_invoice_status(payment_schedule: list[dict], reference_date: str)` both take the
actual fixture content / a reference date as **required arguments** — there is no
internal fallback to load fixtures themselves.

On the live path, `build_ops_agent()` registers exactly these same three tools
(`check_scope_creep`, `check_invoice_status`, `draft_status_update`) — but **no**
fixture-loading tool (`load_client_thread`/`load_payment_schedule`) is registered on
`ops_agent`, and `_supervisor_ops_runner`'s prompt never includes the fixture content or a
reference date:

```python
supervisor(
    "Run ops checks for this signed contract and fixture data: "
    f"{contract.model_dump_json()}, fixture={fixture}"
)
```

This passes only the `ContractSlice` JSON (`{text, payment_schedule}` where
`payment_schedule` is the *proposal-stage* `PaymentMilestone` shape —
`label`/`amount`/`due_marker`, exactly the schema 06-RESEARCH.md Pitfall 2 warns must
never be conflated with the ops-stage `due_date`/`paid` shape) and the bare string
`fixture=creep`/`fixture=clean`. Consequences for the LLM trying to satisfy the system
prompt ("Always call check_scope_creep and check_invoice_status"):

- `check_scope_creep`'s `thread_messages` argument has **no source anywhere in the
  prompt or toolset** — the client-thread fixture content (`sample_client_thread.json` /
  `_clean.json`) is never surfaced to the agent. The model must invent messages to pass,
  defeating OPS-01's entire purpose (compare *real* incoming messages against the SOW).
- `check_invoice_status`'s `payment_schedule` argument has no correctly-shaped source
  either — the only "payment schedule" data present is `contract.payment_schedule`
  (`due_marker`, no `due_date`), which would raise `KeyError: 'due_date'` inside the tool
  if the model naively forwards it (caught by `api.py`'s generic `except Exception`, so
  it degrades to a 503 rather than a 500 — but the ops check itself never runs correctly).
- `reference_date` (required, no default — Pitfall 1) is never supplied to the agent at
  all; nothing in the prompt tells the model what "today" is.

`contract_text` is the *only* one of these four required tool arguments the agent can
derive correctly (it's inside `contract.model_dump_json()`'s `text` field).

Net effect: `OPS_BACKEND=supervisor` — the path D-08 designates for the "live four-agent
Bedrock trace" that is the project's core judged artifact (ORC-01/SC1) — cannot produce a
fixture-grounded, correct `OpsResult`. It will either hallucinate plausible-looking flags,
error out via a tool-call validation failure, or degrade to a 503. This is invisible to the
automated suite (manual-verification-only per D-08) but will surface the first time a
human runs the live trace, exactly the scenario D-08 exists to gate.

**Fix:** Load the fixture data and compute the reference date at the `_supervisor_ops_runner`
call site (same call site pattern already used for the deterministic runner) and inline
them into the prompt, mirroring how `_supervisor_proposal_runner` inlines
`job.model_dump_json()`:

```python
def _supervisor_ops_runner(contract: ContractSlice, fixture: str) -> OpsResult:
    from datetime import date
    from agents.supervisor import build_full_supervisor, extract_ops_result

    thread_messages = load_client_thread(fixture)
    payment_schedule = load_payment_schedule(fixture)
    reference_date = date.today().isoformat()

    supervisor = build_full_supervisor()
    supervisor(
        "Run ops checks for this signed contract.\n"
        f"contract={contract.model_dump_json()}\n"
        f"thread_messages={thread_messages!r}\n"
        f"payment_schedule={payment_schedule!r}\n"
        f"reference_date={reference_date!r}"
    )
    return extract_ops_result(supervisor.messages)
```

(Alternative: register two additional `@tool`-decorated fixture-loading functions on
`ops_agent` so the model fetches the data itself — either approach closes the gap; the
important invariant is that the live path must have *some* route to the real fixture
content and a real reference date, which it currently has none of.)

## Medium Issues

### MD-01: REC-03 AST guard does not scan `backend/fixtures/`

**Disposition: FIXED.** `SCAN_DIRS` in `backend/tests/test_single_writer.py`
now includes `"fixtures"`. See 06-REVIEW-FIX.md.

**File:** `backend/tests/test_single_writer.py:13` (`SCAN_DIRS = ["agents", "tools"]`), `backend/fixtures/loader.py:7-11`, `backend/fixtures/__init__.py:3-4`

**Issue:** `fixtures/loader.py` and `fixtures/__init__.py` both carry a docstring
asserting they must never import the store, explicitly noting "even though
backend/fixtures/ is not itself scanned" — but that's exactly the gap: `SCAN_DIRS` only
covers `agents/` and `tools/`. Today there is no store import in `fixtures/`, so REC-03
is not currently violated, but the enforcement mechanism that's supposed to make this a
structural guarantee (rather than a comment-only convention) silently does not cover this
directory. Since fixtures load real filesystem data that will grow in Phase 7 (README/demo
work), this is the kind of gap that's easy to regress past without any test catching it.

**Fix:** Add `"fixtures"` to `SCAN_DIRS` in `test_single_writer.py`:
```python
SCAN_DIRS = ["agents", "tools", "fixtures"]
```

### MD-02: Fixture loader raises an unhelpful bare `KeyError` on an unrecognized variant

**Disposition: FIXED.** `load_client_thread`/`load_payment_schedule` in
`backend/fixtures/loader.py` now raise `ValueError(f"unknown fixture variant
{variant!r}; expected 'creep' or 'clean'")` before the `_VARIANT_SUFFIX`
lookup. See 06-REVIEW-FIX.md.

**File:** `backend/fixtures/loader.py:28, 37` (`_VARIANT_SUFFIX[variant]`)

**Issue:** `load_client_thread`/`load_payment_schedule` index `_VARIANT_SUFFIX` by the raw
`variant` argument. Today this is safe from path traversal (dict lookup, not string
interpolation) and is only ever called with an API-validated `Literal["creep","clean"]`
value from `api.py` — but the functions themselves have no input validation, so a bare,
unqualified `KeyError: 'whatever-was-passed'` propagates to any future caller (a script, a
notebook, a Phase-7 demo harness) that invokes the loader directly with a typo'd or
unsupported variant, rather than a clear, actionable error.

**Fix:**
```python
def load_client_thread(variant: str = "creep") -> list[str]:
    if variant not in _VARIANT_SUFFIX:
        raise ValueError(f"unknown fixture variant {variant!r}; expected 'creep' or 'clean'")
    ...
```

## Low Issues

### LO-01: Triplicated toolResult-scanning logic in `supervisor.py`

**Disposition: DEFERRED.** 06-CONTEXT.md D-01 and 06-RESEARCH.md Open
Question 1 explicitly require leaving `extract_triage_result`/
`extract_proposal_result` untouched (a prohibition test in
`test_full_supervisor_wiring.py` asserts they are unchanged); refactoring
them would risk that invariant. Deliberate tradeoff, not this phase's work.

**File:** `backend/agents/supervisor.py:48-67` (`extract_triage_result`), `:99-118`
(`extract_proposal_result`), `:179-226` (`_find_tool_result_json`)

**Issue:** `extract_triage_result` and `extract_proposal_result` are near-line-for-line
copies of each other (single-pass first-`json`-block scan), and `_find_tool_result_json`
re-implements the same block-walking/defensive-`isinstance` pattern a third time (as a
two-pass name-disambiguated version). 06-RESEARCH.md's "Open Questions" section explicitly
considered and deferred unifying these ("leave `extract_triage_result`/
`extract_proposal_result` untouched... add the new shared helper alongside"), so this is a
known, deliberate tradeoff — but from a pure maintainability standpoint three copies of
the same message-walking algorithm (one of which is a strict superset of the other two)
is real duplication that will need to stay in sync by hand if the underlying
`ToolUse`/`ToolResult` shape ever changes.

**Fix:** Consider (non-blocking, can be deferred past this phase per the research
decision): rewrite `extract_triage_result`/`extract_proposal_result` as one-line callers of
`_find_tool_result_json(messages, "gig_triage_agent")` /
`_find_tool_result_json(messages, "proposal_contract_agent")`, since the two-pass
algorithm is behavior-preserving for a single-tool supervisor (the toolUse-index pass is a
strict superset of a first-match scan when there's only one possible tool name).

### LO-02: `check_scope_creep`'s "already-in-SOW" exemption is a raw substring test, not a semantic check

**Disposition: DEFERRED.** Explicitly [ASSUMED]/discretionary per
06-RESEARCH.md Assumption A1; reviewer states "No change required for this
phase's demo scope." Correct against current fixtures/tests.

**File:** `backend/tools/check_scope_creep.py:64` (`if matched in lowered_contract: continue`)

**Issue:** A flagged message is suppressed only if the *exact matched signal phrase*
(e.g. `"can you also"`) is found verbatim as a substring anywhere in the lowercased
contract text — not because the specific ask is actually covered by the SOW. This is
explicitly `[ASSUMED]`/discretionary per 06-RESEARCH.md (Assumption A1) and works
correctly against the current fixtures/tests, but it's a fragile heuristic: any future SOW
template that happens to contain one of these seven fixed phrases verbatim (e.g. a
templated line like "Additionally, could you provide feedback within 5 days") would
silently suppress a genuine creep flag containing the same phrase, and vice versa — a
phrase match says nothing about whether the *specific ask* is in scope.

**Fix:** No change required for this phase's demo scope; if this logic is extended past
the fixed 7-phrase list, consider matching on a per-deliverable checklist extracted from
the contract (e.g. the three enumerated `Deliverables (per proposal)` lines) rather than a
flat substring check against the whole contract text.

### LO-03: `OpsSlice.status_updates` is always replaced wholesale, never accumulated, despite the plural/list-typed field name

**Disposition: DEFERRED.** No requirement asks for accumulation; current
behavior is internally consistent (all ops flags recompute per call);
renaming/changing `OpsSlice` would alter the persisted record shape locked
by D-07 with no requirement driving it.

**File:** `backend/api.py:243-247` (`record.ops = OpsSlice(status_updates=[ops_result.status_update], ...)`)

**Issue:** Every `/advance?stage=ops` call rebuilds `record.ops` from scratch, so
`status_updates` is always a single-element list containing only the most recent status
update — any prior status update from an earlier `/advance?stage=ops` call on the same
engagement is discarded, not appended. This is internally consistent (scope-creep/invoice
flags are likewise fully recomputed each call, never accumulated, so nothing about this
phase's behavior is actually broken by it) but the plural field name/list type reads as if
it's meant to be a running history, which it currently isn't. Not a functional defect
given current requirements (no test or requirement asks for accumulation), but worth a
naming/behavior reconciliation before this becomes an assumed invariant elsewhere.

**Fix:** Either rename the field to `status_update: Optional[StatusUpdate]` (singular) to
match its actual "latest snapshot" semantics, or change `api.py` to append
(`record.ops.status_updates + [ops_result.status_update]` when `record.ops` already
exists) if accumulating history across repeated ops-stage calls is the intended demo
behavior.

---

_Reviewed: 2026-09-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
