---
phase: 07-full-demo-verification-submission-docs
plan: 01
subsystem: testing
tags: [fastapi, testclient, pytest, ast, demo-tooling]

requires:
  - phase: 06-ops-agent-fixtures-full-supervisor-wiring
    provides: the integrated capture -> proposal -> ops pipeline (/capture, /advance?stage=proposal|ops), FileEngagementStore, and the creep/clean ops fixtures this plan's demo entrypoint drives
provides:
  - "backend/scripts/run_demo.py — one-command CLI that drives the full pipeline in-process via TestClient(app), for three deterministic scenarios (creep/clean/ambiguous)"
  - "backend/tests/test_demo_determinism.py — pytest proof that the full fixture set is byte-identical across 3 runs on curated decision fields, plus an end-to-end slice-population test"
  - "backend/tests/test_single_writer.py's SCAN_DIRS now covers backend/scripts/, machine-enforcing REC-03 for run_demo.py and every future script"
affects: [07-02-full-demo-verification-submission-docs]

actuals:
  tokens: 2830
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Demo entrypoints as thin TestClient(app) CLI drivers over the unmodified FastAPI app, never overriding get_store — the demo behaves like a real run, not a test double."
    - "Determinism proofs compare a curated decision-field dict that explicitly excludes wall-clock/UUID-derived fields (engagement_id, invoice_flags[].days_overdue) rather than raw model_dump() equality."

key-files:
  created:
    - backend/scripts/run_demo.py
    - backend/tests/test_demo_determinism.py
  modified:
    - backend/tests/test_single_writer.py

key-decisions:
  - "run_demo.py's last stdout line is always a stable machine-parseable SUMMARY line (fixture=/ops_cards=... or scenario=ambiguous/proposal=...) so the demo run is self-verifying without parsing full narration output."
  - "Extended test_single_writer.py's SCAN_DIRS to include \"scripts\" (Task 3) rather than leaving REC-03 enforcement to construction-only discipline — closes the gap RESEARCH.md Pitfall 4 flagged."

patterns-established:
  - "Pattern: any future backend/scripts/*.py entrypoint is now automatically guarded against importing the store, by the same ast-based test that covers agents/tools/fixtures."

requirements-completed: [DEMO-02]

coverage:
  - id: D1
    description: "run_demo.py runs capture -> proposal -> ops end-to-end from one command with no manual glue steps (DEMO-02/SC1)"
    requirement: "DEMO-02"
    verification:
      - kind: manual_procedural
        ref: "cd backend && python3 -m scripts.run_demo --fixture creep (exit 0, SUMMARY fixture=creep triage_verdict=apply ops_cards=2)"
        status: pass
      - kind: manual_procedural
        ref: "cd backend && python3 -m scripts.run_demo --fixture clean (exit 0, SUMMARY fixture=clean triage_verdict=apply ops_cards=0)"
        status: pass
      - kind: manual_procedural
        ref: "cd backend && python3 -m scripts.run_demo --ambiguous (exit 0, SUMMARY scenario=ambiguous triage_verdict=apply proposal=needs_human_input)"
        status: pass
      - kind: integration
        ref: "tests/test_demo_determinism.py#test_pipeline_populates_all_stage_slices"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full fixture set (creep + clean) is byte-identical across 3 runs on curated decision fields, excluding engagement_id and invoice_flags[].days_overdue (DEMO-02/SC2)"
    requirement: "DEMO-02"
    verification:
      - kind: integration
        ref: "tests/test_demo_determinism.py#test_full_fixture_set_is_deterministic_across_three_runs"
        status: pass
    human_judgment: false
  - id: D3
    description: "run_demo.py never imports the store directly, and the REC-03 single-writer guard now machine-enforces this for backend/scripts/ (T-07-STORE)"
    requirement: "DEMO-02"
    verification:
      - kind: unit
        ref: "tests/test_single_writer.py#test_no_agent_or_tool_module_imports_store"
        status: pass
      - kind: other
        ref: "grep -c '\"scripts\"' tests/test_single_writer.py (== 2, confirms SCAN_DIRS addition)"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 1: Deterministic Demo Tracer Summary

**`backend/scripts/run_demo.py` drives capture -> proposal -> ops in one command via `TestClient(app)`, proven byte-identical across 3 runs on curated decision fields, with REC-03's single-writer guard now covering `backend/scripts/`.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-09-09T21:33:00Z
- **Completed:** 2026-09-09T21:35:19Z
- **Tasks:** 3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `backend/scripts/run_demo.py`: a thin CLI over the unmodified FastAPI app (`TestClient(app)`, no `dependency_overrides`) that runs `POST /capture` -> `POST /advance?stage=proposal` -> `POST /advance?stage=ops&fixture=...`, printing the triage verdict, proposal/contract (or escalation), and ops escalation cards; supports `--fixture creep|clean` and `--ambiguous`; every run ends with a stable machine-parseable `SUMMARY ...` line.
- `backend/tests/test_demo_determinism.py`: proves the creep and clean fixture sets each produce byte-identical curated decision dicts across 3 runs (excluding the per-run UUID `engagement_id` and the wall-clock-derived `invoice_flags[].days_overdue`), plus a second test confirming one full run populates every stage slice (triage/proposal/contract/ops).
- Extended `backend/tests/test_single_writer.py`'s `SCAN_DIRS` to include `"scripts"`, so the existing ast-based REC-03 import-graph guard now permanently covers `backend/scripts/*.py` (T-07-STORE), not just `agents/`, `tools/`, and `fixtures/`.

## Task Commits

Each task was committed atomically:

1. **Task 1: TRACER — run_demo.py drives capture -> proposal -> ops end-to-end, one command** - `f6bef8b` (feat)
2. **Task 2: Determinism proof — full fixture set 3x identical + pipeline populates all slices** - `0a013cf` (test)
3. **Task 3: Harden the REC-03 single-writer guard to cover backend/scripts/** - `7140a9e` (test)

**Plan metadata:** (pending — this commit)

## Files Created/Modified
- `backend/scripts/run_demo.py` - one-command demo entrypoint, `TestClient(app)`-driven, three scenarios (creep/clean/ambiguous)
- `backend/tests/test_demo_determinism.py` - 3x-identical determinism proof + end-to-end slice-population test
- `backend/tests/test_single_writer.py` - `SCAN_DIRS` now includes `"scripts"`

## Decisions Made
- Reused the exact `TestClient`/route-call sequence verified in `test_advance_endpoint.py` rather than inventing a new call shape, per RESEARCH.md Pattern 1.
- Chose a curated decision-field dict (not full `model_dump()` equality) for the determinism assertion, per CONTEXT.md's "Claude's Discretion" and RESEARCH.md Pitfall 1 — full equality would make the test flakily fail across a day boundary due to `days_overdue`.
- Did not add a `get_store` override in `run_demo.py` — it exercises the real default `FileEngagementStore` under the gitignored `backend/data/engagements/`, matching D-01's "behaves like a real run" intent.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The verified invocation (`cd backend && python3 -m scripts.run_demo --fixture creep|clean` / `--ambiguous`) and its exact SUMMARY-line output are ready for Plan 07-02's `docs/demo-script.md` to cite as the ≤5-minute walkthrough's commands.
- Full suite: 120 tests passing (118 baseline + 2 new determinism tests), offline, no AWS credentials required.
- No blockers for Plan 07-02 (README, LICENSE, architecture diagram, demo script, submission-presence tests).

---
*Phase: 07-full-demo-verification-submission-docs*
*Completed: 2026-09-09*

## Self-Check: PASSED

- FOUND: backend/scripts/run_demo.py
- FOUND: backend/tests/test_demo_determinism.py
- FOUND: commit f6bef8b (Task 1)
- FOUND: commit 0a013cf (Task 2)
- FOUND: commit 7140a9e (Task 3)
- Full suite re-run: `cd backend && python3 -m pytest -q` -> 120 passed
- Plan-level `<verification>` re-run: all three `run_demo.py` scenarios exit 0 with expected SUMMARY lines
