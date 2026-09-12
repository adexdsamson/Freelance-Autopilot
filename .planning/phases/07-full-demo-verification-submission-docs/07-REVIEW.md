---
phase: 07-full-demo-verification-submission-docs
reviewed: 2026-09-09T21:50:06Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - backend/scripts/run_demo.py
  - backend/tests/test_demo_determinism.py
  - backend/tests/test_single_writer.py
  - backend/tests/test_submission_presence.py
  - README.md
  - LICENSE
  - docs/architecture.md
  - docs/demo-script.md
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
fix_status: all_fixed
fixed_at: 2026-09-09T22:40:00Z
fix_report: 07-REVIEW-FIX.md
dispositions:
  CR-01: fixed (7bbd8e9)
  WR-01: fixed (6f5fcb3)
  WR-02: fixed (806d904)
  IN-01: fixed (6725771)
  IN-02: fixed (6725771)
  IN-03: fixed (7bbd8e9)
---

# Phase 7: Code Review Report

**Reviewed:** 2026-09-09T21:50:06Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

I read all 8 files, cross-referenced them against `backend/agents/{supervisor,triage_runner,proposal_runner,ops_runner}.py`, `backend/api.py`, `backend/models/engagement_record.py`, and every deterministic `backend/tools/*.py` gate, and executed the actual commands cited in `README.md` and `docs/demo-script.md` (`python3 -m scripts.run_demo --fixture creep|clean`, `--ambiguous`, and `uvicorn api:app`) against the real repo — all ran correctly and produced the exact output the docs claim (`ops_cards=2` for `creep`, `ops_cards=0` for `clean`, `needs_human_input=True` for `--ambiguous`). I also independently verified `test_submission_presence.py`'s `parents[2]` resolves to the true repo root (not `backend/`), and confirmed `run_demo.py` imports only `api.app` — never `store` — so the REC-03 single-writer guard's extension of `SCAN_DIRS` to include `"scripts"` is not just present but actually enforceable and correctly passing. No hardcoded secrets, AWS credential literals, or the user's email appear anywhere in the reviewed docs/code. `pytest` runs 124/124 green.

The one real defect is in `docs/architecture.md`: the Mermaid diagram draws a call relationship between the triage/proposal live-path supervisor runners and `build_full_supervisor()` that does not exist in the code — three genuinely separate, non-overlapping Supervisor builder functions are drawn converging into one node. This directly contradicts D-05's "must match the actual object graph... never invented" requirement and is classified as an invented-relationship finding per this review's explicit mandate. A related, softer inaccuracy exists in `docs/demo-script.md`'s Beat 4 framing of "four distinct agent invocations." Two coverage/robustness gaps (an untested ambiguous-escalation determinism path, and a weak README section-presence assertion) round out the findings, plus two low-severity quality nits in `run_demo.py`.

## Critical Issues

### CR-01: Architecture diagram invents a converged-supervisor relationship that doesn't exist in the code

**File:** `docs/architecture.md:41-51`
**Issue:** The Mermaid diagram draws `sup_triage --> full_sup` and `sup_prop --> full_sup`, visually asserting that `_supervisor_triage_runner` (`backend/agents/triage_runner.py:37-47`) and `_supervisor_proposal_runner` (`backend/agents/proposal_runner.py:60-74`) route into `build_full_supervisor()`. This is false. Reading the actual code:
- `_supervisor_triage_runner` calls `build_supervisor()` (`backend/agents/supervisor.py:24-45`), a Supervisor wired with **only** the `gig_triage_agent` tool.
- `_supervisor_proposal_runner` calls `build_proposal_supervisor()` (`backend/agents/supervisor.py:70-96`), a Supervisor wired with **only** the `proposal_contract_agent` tool. Its own docstring states: *"a SEPARATE, stage-scoped Supervisor... NOT an extension of `build_supervisor()`."*
- Only `_supervisor_ops_runner` (`backend/agents/ops_runner.py:72-105`) calls `build_full_supervisor()`, whose own docstring states: *"This is ADDITIVE -- `build_supervisor()`/`build_proposal_supervisor()` above are left completely untouched (D-01 prohibition); this is a third, separate builder."*

The diagram's node labels for `sup_triage`/`sup_prop` correctly name `build_supervisor()`/`build_proposal_supervisor()`, but the edges into `full_sup` invent a shared-object-graph relationship among three independent Supervisor instances. This directly violates D-05's locked requirement that the diagram "must match the actual object graph... verified against real symbols, not invented," and is compounded by `docs/demo-script.md:54-60` (Beat 4), which claims re-running any beat with all three `*_BACKEND=supervisor` vars set shows "four distinct, independently traceable agent invocations: the Supervisor plus the three specialists it wraps" for "the same pipeline" — this is only even approximately true for the ops stage alone, and `build_full_supervisor()`'s own system prompt ("never call more than one specialist tool in a single turn") means even a single ops advance invokes only 2 agents, not 4. A live full-pipeline run actually constructs three unrelated Supervisor instances (2 agents each = 6 total), never a single 4-agent trace.

**Fix:**
```
- Split the diagram's "sup_triage" and "sup_prop" nodes so they each point ONLY at their
  own specialist (gig_triage_agent, proposal_contract_agent respectively), never at
  full_sup.
- Keep full_sup ("build_full_supervisor()") fed ONLY by sup_ops, pointing at all three
  specialists (triage_agent, prop_agent, ops_agent) as it does today — that part is
  correct for the ops-stage live path.
- Reword docs/demo-script.md Beat 4 to describe what actually happens: each stage
  independently routes through its own stage-scoped Supervisor; only the ops stage's
  Supervisor has all three specialists registered as tools (though its system prompt
  still restricts it to calling exactly one per turn).
```

**Disposition: fixed (commit `7bbd8e9`).** `docs/architecture.md`'s Mermaid diagram now routes `sup_triage --> gig_triage_agent` and `sup_prop --> proposal_contract_agent` directly, with `full_sup` fed only by `sup_ops` and pointing at all three specialists — matching `backend/agents/supervisor.py`'s three independent builders (`build_supervisor`/`build_proposal_supervisor`/`build_full_supervisor`, verified by symbol grep). The Component Table's "Supervisor" row was also updated to describe all three builders instead of only `build_full_supervisor`. `docs/demo-script.md` Beat 4 reworded per IN-03 below.

## Warnings

### WR-01: Ambiguous-escalation path (Beat 3 / `--ambiguous`) has no automated determinism test

**File:** `backend/tests/test_demo_determinism.py:72-77`
**Issue:** `test_full_fixture_set_is_deterministic_across_three_runs` proves 3× determinism only for `CLEAR_SCOPE_JOB` against the `creep`/`clean` ops fixtures. `run_demo.py`'s `--ambiguous` scenario (`AMBIGUOUS_JOB`, exercised in `docs/demo-script.md` Beat 3) — the proposal-stage `needs_human_input` escalation — is never run 3× and asserted identical anywhere in the automated suite. Since D-02/SC2 exists specifically as the "anti-nondeterministic-demo guard" and this is one of the three scripted demo beats, its determinism claim currently rests entirely on manual inspection rather than a machine-verified assertion.
**Fix:**
```python
def test_ambiguous_escalation_is_deterministic_across_three_runs(client):
    runs = []
    for _ in range(3):
        capture = client.post("/capture", json=AMBIGUOUS_JOB)
        assert capture.status_code == 200
        eid = capture.json()["engagement_id"]
        resp = client.post(f"/engagements/{eid}/advance", params={"stage": "proposal"})
        assert resp.status_code == 200
        body = resp.json()["proposal"]
        runs.append({"needs_human_input": body["needs_human_input"], "question": body["question"]})
    assert runs[0] == runs[1] == runs[2]
```

**Disposition: fixed (commit `6f5fcb3`).** Added `test_ambiguous_escalation_is_deterministic_across_three_runs` to `backend/tests/test_demo_determinism.py` using the same `AMBIGUOUS_JOB` shape `run_demo.py` uses. Verified passing (3 tests in file, 125 total in suite).

### WR-02: README presence check would false-pass even if the actual Setup/Run/Test headings were removed

**File:** `backend/tests/test_submission_presence.py:33-39`
**Issue:** `test_readme_exists_with_required_sections` only asserts the bare substrings `"setup"`, `"run"`, `"test"` appear *anywhere* in the lower-cased README text — not that they exist as actual section headings. `"test"` in particular is a common substring inside unrelated words (`TestClient`, `latest`, `attest`, etc.) and even `docs/demo-script.md`-style prose. If a future edit accidentally deleted the real `## Setup`/`## Run`/`## Test` headings but left any incidental occurrence of those words elsewhere in the file, this presence test — whose entire purpose is to catch exactly that regression (D-07(c)) — would still pass.
**Fix:**
```python
import re

def test_readme_exists_with_required_sections():
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.exists(), f"expected README.md at repo root: {readme_path}"
    text = readme_path.read_text()
    for heading in ("Setup", "Run", "Test"):
        assert re.search(rf"^#{{1,6}}\s*{heading}\b", text, re.MULTILINE | re.IGNORECASE), (
            f"README.md is missing a '## {heading}' heading"
        )
```

**Disposition: fixed (commit `806d904`).** Applied the reviewer's regex fix verbatim to `backend/tests/test_submission_presence.py`. Checked README.md's actual headings first (`## Setup`, `## Run`, `## Test` — already match the required words exactly), so no README changes were needed to reconcile; the fixed test passes against the real README unchanged.

## Info

### IN-01: `TestClient` constructed without a context manager, unlike the project's own fixture idiom

**File:** `backend/scripts/run_demo.py:45-50`
**Issue:** `build_client()` returns `TestClient(app)` directly. `backend/tests/conftest.py`'s `client` fixture instead uses `with TestClient(app) as test_client: yield test_client`, which triggers FastAPI/Starlette lifespan (`startup`/`shutdown`) events. `backend/api.py` has no lifespan handlers today so this is harmless in practice, but it's an inconsistent pattern versus the codebase's own established idiom, and would silently stop firing lifespan events if any are added later without anyone noticing (no error, just silently skipped startup logic).
**Fix:**
```python
def main() -> None:
    ...
    with TestClient(app) as client:
        run_pipeline(client, args.fixture, args.ambiguous)
```

**Disposition: fixed (commit `6725771`).** `main()` now does `with build_client() as client:` (kept the existing `build_client()` factory rather than inlining `TestClient(app)`, since it's still referenced only here and preserves the D-01/Pattern 1 "unmodified app, no dependency_overrides" docstring contract).

### IN-02: Unhandled `HTTPStatusError` surfaces a raw traceback during the recorded demo

**File:** `backend/scripts/run_demo.py:60,71,94`
**Issue:** Each `client.post(...).raise_for_status()` call is unguarded. Any unexpected non-2xx response (e.g., a 409/404 from a stale/reused `backend/data/engagements/` directory, or a future regression in the deterministic runners) crashes the script with a raw Python traceback rather than a clean, demo-appropriate error message — a real risk for the ≤5-minute recorded walkthrough this phase is explicitly built to de-risk (the script's own docstring already flags demo-day operator error as "a real risk").
**Fix:**
```python
import sys
import httpx

try:
    capture_response.raise_for_status()
except httpx.HTTPStatusError as exc:
    print(f"FATAL: {exc.request.url} returned {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
    sys.exit(1)
```

**Disposition: fixed (commit `6725771`).** Added a shared `_raise_for_status_or_exit()` helper (avoids repeating the try/except three times) and applied it to all three `.raise_for_status()` call sites (capture, proposal advance, ops advance). Re-ran all three demo scenarios end-to-end after the fix (`--fixture creep` → `ops_cards=2`, `--fixture clean` → `ops_cards=0`, `--ambiguous` → `needs_human_input=True`), all exit 0, output unchanged from pre-fix.

### IN-03: `docs/demo-script.md` Beat 4 overstates the live-path agent count (see CR-01)

**File:** `docs/demo-script.md:54-60`
**Issue:** Restated here for traceability — see CR-01 for the full analysis. This entry exists so the fix isn't lost if only `docs/architecture.md` is corrected: Beat 4's "four distinct, independently traceable agent invocations" claim needs its own wording pass independent of the diagram fix.
**Fix:** See CR-01's fix block (third bullet).

**Disposition: fixed (commit `7bbd8e9`, same commit as CR-01).** Beat 4's heading and wording changed from "Live four-agent Bedrock trace" / "four distinct, independently traceable agent invocations... for the same pipeline" to a description of each stage independently routing through its own stage-scoped Supervisor, with only the ops stage's Supervisor registering all three specialists (and its system prompt still restricting it to one specialist call per turn).

---

_Reviewed: 2026-09-09T21:50:06Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
