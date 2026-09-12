---
phase: 07-full-demo-verification-submission-docs
plan: 02
subsystem: testing
tags: [readme, license, mermaid, docs, presence-test, submission]

requires:
  - phase: 07-full-demo-verification-submission-docs (plan 01)
    provides: "backend/scripts/run_demo.py's verified --fixture/--ambiguous CLI contract, cited verbatim in README + demo-script"
provides:
  - "README.md (repo root) — Setup/Run/Test sections citing only verified-working commands, plus a requirements traceability table and manual-only boundary notes"
  - "LICENSE (repo root) — MIT text, Copyright (c) 2026 Freelance Autopilot"
  - "docs/architecture.md — Mermaid flowchart + component table grounded in the real backend/ object graph"
  - "docs/demo-script.md — <=5-minute walkthrough script tied to run_demo.py's exact commands"
  - "backend/tests/test_submission_presence.py — machine-verifies all four artifacts exist with the required shape"
affects: []

actuals:
  tokens: 4241
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Presence tests as plain pathlib + assert-with-message (no ast), resolving the TRUE repo root via parents[2] — one level beyond test_single_writer.py's backend/-only root."
    - "Submission docs cite only RESEARCH-verified commands (python3 -m scripts.run_demo, uvicorn api:app --reload, python3 -m pytest) — never the ModuleNotFoundError-producing forms."

key-files:
  created:
    - README.md
    - LICENSE
    - docs/architecture.md
    - docs/demo-script.md
    - backend/tests/test_submission_presence.py
  modified: []

key-decisions:
  - "README section ordering: value prop -> architecture link -> Setup -> Run -> Test -> traceability table -> manual-only boundaries (CONTEXT.md left ordering to Claude's discretion)."
  - "Architecture diagram reused RESEARCH.md's session-verified Mermaid graph nearly verbatim (it was built by reading every depicted file this session), correcting only the runner-seam labels from 'TRIAGE_BACKEND unset' framing to the literal env-var default value 'placeholder' for clarity."
  - "Demo-script beat 3 reuses the exact ambiguous-job input text ('Looking for someone to help with ongoing design work.') already proven deterministic in test_advance_endpoint.py, rather than inventing new wording."
  - "LICENSE copyright holder is the locked CONTEXT.md D-04 string 'Freelance Autopilot' with no email address; README flags it as user-adjustable per D-04."

patterns-established:
  - "Submission-artifact presence is machine-verified in the same offline pytest suite the rest of the project uses, not a separate shell script — one verification surface."

requirements-completed: [DEMO-03, DEMO-04, DEMO-05]

coverage:
  - id: D1
    description: "Repo-root LICENSE (MIT) and README.md with Setup/Run/Test sections citing only verified-working commands exist (DEMO-03, DEMO-04)"
    requirement: "DEMO-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_submission_presence.py#test_license_file_exists_at_repo_root"
        status: pass
      - kind: unit
        ref: "backend/tests/test_submission_presence.py#test_readme_exists_with_required_sections"
        status: pass
      - kind: other
        ref: "grep -q 'Permission is hereby granted' LICENSE && grep -qi setup/run/test README.md (task-level verify)"
        status: pass
    human_judgment: false
  - id: D2
    description: "docs/architecture.md contains a Mermaid diagram naming only real backend/ symbols, and docs/demo-script.md is a <=5-minute walkthrough tied to run_demo.py's exact commands (DEMO-05)"
    requirement: "DEMO-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_submission_presence.py#test_architecture_doc_has_mermaid_block"
        status: pass
      - kind: unit
        ref: "backend/tests/test_submission_presence.py#test_demo_script_doc_exists"
        status: pass
      - kind: other
        ref: "grep -q build_full_supervisor/FileEngagementStore docs/architecture.md && grep -q run_demo docs/demo-script.md (task-level verify)"
        status: pass
    human_judgment: false
  - id: D3
    description: "No AWS credential, secret, or email address appears in README.md, LICENSE, or docs/* (T-07-SECRET)"
    requirement: "DEMO-03"
    verification:
      - kind: other
        ref: "grep -RniE aws_secret_access_key|aws_access_key_id|ai@mainlandtech.com README.md LICENSE docs/architecture.md docs/demo-script.md (negative grep, task-level verify x2)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A pytest presence test resolves the TRUE repo root and asserts LICENSE, README.md, docs/architecture.md, and docs/demo-script.md all exist with the required shape (D-07(c)(d))"
    requirement: "DEMO-05"
    verification:
      - kind: unit
        ref: "backend/tests/test_submission_presence.py (all 4 tests, full offline suite: 124 passed)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-09-09
status: complete
---

# Phase 7 Plan 2: Full Demo Verification & Submission Docs Summary

**Repo-root README + MIT LICENSE, a Mermaid architecture diagram grounded in the real `backend/` object graph, a <=5-minute demo script tied to `run_demo.py`'s exact CLI, and a pytest presence test machine-verifying all four — 124/124 tests green.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-09-09T21:38:00Z
- **Completed:** 2026-09-09T21:41:38Z
- **Tasks:** 3
- **Files modified:** 5 (all created)

## Accomplishments
- `README.md` (repo root): one-line value prop, architecture overview linking `docs/architecture.md`, Setup (Python 3.10+, `pip install -r backend/requirements.txt`, generic boto3-chain credential note), Run (`cd backend && python3 -m scripts.run_demo --fixture creep|clean` / `--ambiguous`, `cd backend && uvicorn api:app --reload`), Test (`cd backend && python3 -m pytest`), a requirements-traceability table, and the three manual-only boundary notes (Chrome extension, recorded video, live Bedrock trace).
- `LICENSE` (repo root): standard MIT text, `Copyright (c) 2026 Freelance Autopilot`, no email/secret literal.
- `docs/architecture.md`: a Mermaid `flowchart` fenced block naming only real `backend/` symbols (`build_full_supervisor`, the three specialists as agents-as-tools, the `TriageRunner`/`ProposalRunner`/`OpsRunner` DI seams with their deterministic-default + `*_BACKEND=supervisor` live paths, `api.py` as sole `EngagementStore` writer, `EngagementStore`/`FileEngagementStore`, `fixtures/loader.py`), plus a component table; the Chrome MV3 extension is drawn dashed/planned (Phase 4).
- `docs/demo-script.md`: a <=5-minute walkthrough with four beats, each citing a real `run_demo.py` command — creep fixture (`apply` verdict, proposal+contract, 2 ops cards), clean fixture (0 ops cards, proves conditional not hardcoded), ambiguous job (`needs_human_input` escalation, ops skipped), and the live four-agent Bedrock trace as an explicit manual step.
- `backend/tests/test_submission_presence.py`: four pytest functions resolving the TRUE repo root via `Path(__file__).resolve().parents[2]` and asserting LICENSE (MIT text), README.md (Setup/Run/Test sections), docs/architecture.md (mermaid fence), and docs/demo-script.md all exist.

## Task Commits

Each task was committed atomically:

1. **Task 1: LICENSE (MIT) + README.md at repo root** - `0071820` (docs)
2. **Task 2: docs/architecture.md + docs/demo-script.md** - `397ee69` (docs)
3. **Task 3: test_submission_presence.py** - `854bc03` (test)

**Plan metadata:** (pending — this commit)

## Files Created/Modified
- `README.md` - repo-root README with Setup/Run/Test, architecture link, traceability table, manual-only boundaries
- `LICENSE` - repo-root MIT license text
- `docs/architecture.md` - Mermaid architecture diagram + component table
- `docs/demo-script.md` - <=5-minute recorded-walkthrough script
- `backend/tests/test_submission_presence.py` - presence/shape test for all four artifacts

## Decisions Made
- README section ordering left to discretion per CONTEXT.md: value prop -> architecture link -> Setup -> Run -> Test -> traceability -> manual-only boundaries.
- Reused RESEARCH.md's session-verified Mermaid diagram nearly verbatim (already built from reading every depicted file), correcting only the runner-seam edge labels to name the literal `placeholder` default env-var value instead of "unset", per RESEARCH.md's own correction note.
- Demo-script beat 3 reuses the exact ambiguous-job text already proven deterministic in `test_advance_endpoint.py`, rather than inventing new wording.
- LICENSE copyright holder uses the locked CONTEXT.md D-04 string with no email address; README explicitly flags it as user-adjustable.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All Phase 7 requirements (DEMO-02 from Plan 07-01, DEMO-03/04/05 from this plan) are now machine-verified complete.
- Full suite: 124 tests passing (120 from Plan 07-01 + 4 new presence tests), offline, no AWS credentials required.
- Repo is submittable: LICENSE + README at repo root, docs/architecture.md + docs/demo-script.md present, all four verified by `test_submission_presence.py`.
- No blockers for `/gsd-verify-work` or milestone completion.

---
*Phase: 07-full-demo-verification-submission-docs*
*Completed: 2026-09-09*

## Self-Check: PASSED

- FOUND: README.md
- FOUND: LICENSE
- FOUND: docs/architecture.md
- FOUND: docs/demo-script.md
- FOUND: backend/tests/test_submission_presence.py
- FOUND: commit 0071820 (Task 1)
- FOUND: commit 397ee69 (Task 2)
- FOUND: commit 854bc03 (Task 3)
- Full suite re-run: `cd backend && python3 -m pytest -q` -> 124 passed
- Plan-level `<verification>` re-run: `test -f README.md && test -f LICENSE && test -f docs/architecture.md && test -f docs/demo-script.md && grep -q '```mermaid' docs/architecture.md` -> ALL_PRESENT
