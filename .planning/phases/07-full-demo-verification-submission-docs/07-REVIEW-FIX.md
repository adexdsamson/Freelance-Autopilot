---
phase: 07-full-demo-verification-submission-docs
fixed_at: 2026-09-09T22:40:00Z
review_path: .planning/phases/07-full-demo-verification-submission-docs/07-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-09-09T22:40:00Z
**Source review:** .planning/phases/07-full-demo-verification-submission-docs/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, WR-01, WR-02, IN-01, IN-02, IN-03)
- Fixed: 6
- Skipped: 0

**Verification environment:** `workflow.use_worktrees` is `false` in `.planning/config.json`, so all edits and commits were made directly in the main checkout on branch `gsd/phase-07-full-demo-verification-submission-docs` (no isolated worktree was created). All gate runs below (pytest, demo scenarios, presence tests, secret grep) ran in this same main checkout and are reproducible from it as-is.

## Fixed Issues

### CR-01: Architecture diagram invents a converged-supervisor relationship that doesn't exist in the code

**Files modified:** `docs/architecture.md`, `docs/demo-script.md`
**Commit:** `7bbd8e9`
**Applied fix:** Removed the false `sup_triage --> full_sup` and `sup_prop --> full_sup` Mermaid edges in `docs/architecture.md`. `sup_triage` now points only at `gig_triage_agent`; `sup_prop` only at `proposal_contract_agent`; `full_sup` remains fed only by `sup_ops` and points at all three specialists (unchanged, since that part was already correct). Also updated the Component Table's "Supervisor" row (previously described only `build_full_supervisor`) to name all three separate builders and their scope, for consistency with the corrected diagram. Reworded `docs/demo-script.md` Beat 4 (also folds in IN-03) to drop the "four distinct agent invocations for the same pipeline" claim. Verified every diagram symbol (`build_supervisor`, `build_proposal_supervisor`, `build_full_supervisor`) against `backend/agents/supervisor.py` via grep before finalizing.

### WR-01: Ambiguous-escalation path (Beat 3 / `--ambiguous`) has no automated determinism test

**Files modified:** `backend/tests/test_demo_determinism.py`
**Commit:** `6f5fcb3`
**Applied fix:** Added `test_ambiguous_escalation_is_deterministic_across_three_runs` per the review's fix block, using the same `AMBIGUOUS_JOB` fixture shape `backend/scripts/run_demo.py` uses (added as a module-level constant alongside the existing `CLEAR_SCOPE_JOB`). Captures the job, advances to `stage=proposal`, 3x, and asserts identical `{needs_human_input, question}` across runs. Ran `pytest tests/test_demo_determinism.py -q` — 3 passed.

### WR-02: README presence check would false-pass even if the actual Setup/Run/Test headings were removed

**Files modified:** `backend/tests/test_submission_presence.py`
**Commit:** `806d904`
**Applied fix:** Replaced the bare lower-cased substring check with the reviewer's suggested heading-anchored regex (`^#{1,6}\s*{heading}\b`, case-insensitive, multiline). Read README.md's actual headings first — they are exactly `## Setup`, `## Run`, `## Test` — so no README changes were needed to reconcile; the fixed test passes unchanged against the real file.

### IN-01: `TestClient` constructed without a context manager, unlike the project's own fixture idiom

**Files modified:** `backend/scripts/run_demo.py`
**Commit:** `6725771`
**Applied fix:** `main()` now does `with build_client() as client:` instead of `client = build_client()`, so lifespan (`startup`/`shutdown`) events fire, matching `backend/tests/conftest.py`'s established `client` fixture idiom. Kept the existing `build_client()` factory function rather than inlining `TestClient(app)` directly, since it is still the sole construction point and preserves its docstring's "unmodified app, no dependency_overrides" contract.

### IN-02: Unhandled `HTTPStatusError` surfaces a raw traceback during the recorded demo

**Files modified:** `backend/scripts/run_demo.py`
**Commit:** `6725771`
**Applied fix:** Added a shared `_raise_for_status_or_exit(response)` helper (imports `sys`/`httpx`) that catches `httpx.HTTPStatusError`, prints a `FATAL: {url} returned {status}: {body}` message to stderr, and calls `sys.exit(1)`. Applied it at all three `.raise_for_status()` call sites (capture, proposal advance, ops advance) rather than repeating the try/except three times inline. Kept the script store-import-free (REC-03 — verified `from api import app` is still the only local import). Re-ran the demo end-to-end after the fix: `--fixture creep` → `ops_cards=2`, `--fixture clean` → `ops_cards=0`, `--ambiguous` → `needs_human_input=True`, all exit 0, output identical to pre-fix.

### IN-03: `docs/demo-script.md` Beat 4 overstates the live-path agent count (see CR-01)

**Files modified:** `docs/demo-script.md`
**Commit:** `7bbd8e9` (same commit as CR-01 — folded in per this fix session's scope)
**Applied fix:** Beat 4 heading changed from "Live four-agent Bedrock trace" to "Live Bedrock trace"; body reworded to state that each stage independently routes through its own stage-scoped Supervisor, and only the ops stage's Supervisor (`build_full_supervisor()`) registers all three specialists as tools — while its system prompt still restricts it to calling exactly one specialist per turn, so no single advance call ever invokes more than one specialist.

## Skipped Issues

None — all six in-scope findings were fixed.

## Validation Performed

- `cd backend && python3 -m pytest -q` → **125 passed** (124 pre-existing + 1 new WR-01 test).
- `cd backend && python3 -m pytest tests/test_submission_presence.py -q` → 4 passed.
- `cd backend && python3 -m scripts.run_demo --fixture creep` → exit 0, `SUMMARY fixture=creep triage_verdict=apply ops_cards=2`.
- `cd backend && python3 -m scripts.run_demo --fixture clean` → exit 0, `SUMMARY fixture=clean triage_verdict=apply ops_cards=0`.
- `cd backend && python3 -m scripts.run_demo --ambiguous` → exit 0, `SUMMARY scenario=ambiguous triage_verdict=apply proposal=needs_human_input`.
- Grepped `docs/`, `README.md`, and all touched backend files for `ai@mainlandtech.com` / AWS credential literal patterns (`AKIA`, `aws_secret_access_key`, `aws_access_key_id`) — no matches.
- Grepped `backend/agents/supervisor.py` for `build_supervisor` / `build_proposal_supervisor` / `build_full_supervisor` — all three symbols cited in the corrected architecture diagram exist exactly as named.

---

_Fixed: 2026-09-09T22:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
