---
phase: 07-full-demo-verification-submission-docs
verified: 2026-09-09T23:15:00Z
status: human_needed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
human_verification:
  - test: "Confirm the 'extension capture' front (the literal first hop of Success Criterion 1: 'extension capture -> triage -> ...') is genuinely a Phase 4 dependency not yet built, and that the repo's documented substitute (POST /capture called directly, exactly as the extension would call it) is an acceptable interpretation for demo/judging purposes."
    expected: "README.md's 'Manual-only boundaries' section and docs/architecture.md's dashed extension node are accepted by the developer as the correct scoping of SC1, since Phase 4 (the MV3 extension) is out of this phase's dependency chain per ROADMAP ('Depends on: Phase 4, Phase 6') but is not marked complete in this repo state."
    why_human: "This is a scope/roadmap-sequencing judgment call (is it acceptable that Phase 4 hasn't shipped yet when Phase 7 claims 'satisfies every submission requirement'?), not a code-verifiable fact. The HTTP capture->proposal->ops pipeline itself is fully verified working; only the literal browser-extension capture surface is unbuilt."
  - test: "Record the ≤5-minute walkthrough video per docs/demo-script.md."
    expected: "A recorded video exists demonstrating the four beats."
    why_human: "Recording a video is an explicit human action; docs/demo-script.md documents the script but the video itself cannot be produced or verified by static code inspection."
---

# Phase 7: Full Demo Verification & Submission Docs Verification Report

**Phase Goal:** The complete pipeline is proven deterministic and demo-ready, and the repository satisfies every submission requirement.
**Verified:** 2026-09-09T23:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: `backend/scripts/run_demo.py` drives capture -> proposal -> ops end-to-end in ONE command via TestClient, no manual glue, no AWS creds | ✓ VERIFIED | Ran all three invocations live in this session: `python3 -m scripts.run_demo --fixture creep` -> exit 0, `SUMMARY fixture=creep triage_verdict=apply ops_cards=2`; `--fixture clean` -> exit 0, `ops_cards=0`; `--ambiguous` -> exit 0, `proposal=needs_human_input`. `run_demo.py` imports only `api.app`, `httpx`, `fastapi.testclient`, `argparse`, `sys` — no `store`/`backend.store` import (grep confirmed empty). |
| 2 | SC1 (extension-capture sub-clause) | ⚠️ Documented dependency gap, not a code failure | README.md "Manual-only boundaries" #1 and docs/architecture.md explicitly document the Chrome MV3 extension as a Phase 4 dependency not built on this branch, and state the `POST /capture` call is exactly what the extension would make. Routed to human verification (scope judgment), per the task's explicit instruction to treat this as human_needed/manual, not a code BLOCKER. |
| 3 | SC2: full fixture set (creep+clean) runs 3x -> identical decision fields, excluding engagement_id + invoice_flags[].days_overdue | ✓ VERIFIED | `backend/tests/test_demo_determinism.py::test_full_fixture_set_is_deterministic_across_three_runs` loops fixture in (creep, clean), runs `_run_once` 3x each, asserts `runs[0]==runs[1]==runs[2]` on a curated dict that drops `engagement_id` entirely and strips `days_overdue` from invoice flags. Also `test_ambiguous_escalation_is_deterministic_across_three_runs` (added post-review, WR-01) proves the ambiguous/Beat-3 path 3x-identical on `{needs_human_input, question}`. Ran `pytest tests/test_demo_determinism.py -q` live: 3 passed. |
| 4 | SC3 (DEMO-03 README): repo-root README.md with Setup/Run/Test sections citing verified commands | ✓ VERIFIED | Read README.md: contains `## Setup`, `## Run`, `## Test` headings (verbatim), cites `cd backend && python3 -m scripts.run_demo --fixture creep\|clean`, `--ambiguous`, `cd backend && uvicorn api:app --reload`, `cd backend && python3 -m pytest` — all match the verified-working invocation forms from RESEARCH.md Pitfalls 2/3 (confirmed no bare-script/`uvicorn backend/api.py:app` forms present). |
| 5 | SC3 (DEMO-04 license): repo-root LICENSE with OSI (MIT) text | ✓ VERIFIED | Read LICENSE: full canonical MIT text, "Permission is hereby granted, free of charge...", `Copyright (c) 2026 Freelance Autopilot`. No email/secret. |
| 6 | No AWS creds / email leak in README, LICENSE, docs/* | ✓ VERIFIED | Ran `grep -RniE "aws_secret_access_key|aws_access_key_id|ai@mainlandtech.com" README.md LICENSE docs/architecture.md docs/demo-script.md` live: exit 1 (no matches). |
| 7 | SC4 (DEMO-05 diagram): docs/architecture.md has a mermaid block naming REAL symbols, and does NOT draw the false sup_triage/sup_prop -> build_full_supervisor convergence (per code-review fix CR-01) | ✓ VERIFIED | Read docs/architecture.md and backend/agents/supervisor.py side by side: the diagram routes `sup_triage --> triage_agent` and `sup_prop --> prop_agent` directly (matching `build_supervisor()`/`build_proposal_supervisor()`, each wired to only their own single specialist); `full_sup` ("build_full_supervisor()") is fed only by `sup_ops` and points at all three specialists — matching the code exactly, including the "never call more than one specialist tool in a single turn" system-prompt constraint reflected in demo-script.md Beat 4's corrected wording. All named symbols (build_supervisor, build_proposal_supervisor, build_full_supervisor, FileEngagementStore, EngagementStore, fixtures/loader.py, TriageRunner/ProposalRunner/OpsRunner DI seams) verified present in the real code. |
| 8 | SC4 (DEMO-05 demo-script): docs/demo-script.md exists, tied to run_demo.py, ≤5-min, Beat 4 corrected | ✓ VERIFIED | Read docs/demo-script.md: four beats each cite the exact `python3 -m scripts.run_demo` invocations, narrate the exact observed output (ops_cards=2/0, needs_human_input), and Beat 4 states "each stage independently routes through its own stage-scoped Supervisor... only the ops stage's Supervisor... has all three specialists registered" — matches the corrected architecture.md and the real code, no "four distinct agent invocations for the same pipeline" overstatement remains. |
| 9 | test_submission_presence.py resolves the true repo root (parents[2]) and passes | ✓ VERIFIED | Read the file: `REPO_ROOT = Path(__file__).resolve().parents[2]` (backend/tests -> backend -> repo root). Ran `pytest tests/test_submission_presence.py -q` live: 4 passed. WR-02 fix confirmed applied — README heading check uses `re.search(rf"^#{{1,6}}\s*{heading}\b", ...)`, not a bare substring check. |
| 10 | Full offline suite green (125 passed) | ✓ VERIFIED | Ran `cd backend && python3 -m pytest -q` live: **125 passed, 1 warning** (unrelated httpx deprecation warning), 0 failed. |

**Score:** 8/8 code-verifiable must-haves VERIFIED (Truth #2's extension-capture sub-clause is explicitly out of scope for code verification per this phase's own README/architecture documentation and per the task's instruction; routed to human_verification, not counted as a failure).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/scripts/run_demo.py` | One-command CLI driver, TestClient(app), 3 scenarios | ✓ VERIFIED | Exists, substantive, wired — ran live, produces correct SUMMARY lines for all 3 scenarios. No `store` import. |
| `backend/tests/test_demo_determinism.py` | 3x determinism proof, curated field exclusion | ✓ VERIFIED | Exists, 3 test functions, all pass live. |
| `backend/tests/test_single_writer.py` | SCAN_DIRS includes "scripts" | ✓ VERIFIED | `SCAN_DIRS = ["agents", "tools", "fixtures", "scripts"]`; test passes live. |
| `backend/tests/test_submission_presence.py` | Resolves true repo root, 4 presence assertions | ✓ VERIFIED | `parents[2]` resolution confirmed correct; 4 tests pass live. |
| `README.md` (repo root) | Setup/Run/Test, traceability, no secrets | ✓ VERIFIED | Read in full; matches all must-haves. |
| `LICENSE` (repo root) | MIT OSI text | ✓ VERIFIED | Read in full; canonical MIT text present. |
| `docs/architecture.md` | Mermaid diagram, real object graph, no invented convergence | ✓ VERIFIED | Read in full, cross-checked against backend/agents/supervisor.py; CR-01 fix confirmed applied. |
| `docs/demo-script.md` | ≤5-min walkthrough tied to run_demo.py, Beat 4 corrected | ✓ VERIFIED | Read in full; IN-03 fix confirmed applied. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_demo.py` | `api.app` | `from api import app`; `TestClient(app)` | ✓ WIRED | Confirmed by reading the file and by live execution (all 3 scenarios ran correctly against the real app). |
| `run_demo.py` | Engagement Record store | NEVER direct — only via TestClient HTTP calls | ✓ WIRED (correctly absent) | Grep for `import store`/`from store` in `backend/scripts/*.py`: zero matches. `test_single_writer.py`'s ast-based guard now scans `scripts/` and passes. |
| `docs/architecture.md` diagram | `backend/agents/supervisor.py` real object graph | Symbol-by-symbol cross-read | ✓ WIRED | `build_supervisor`/`build_proposal_supervisor`/`build_full_supervisor` all exist exactly as named and wired exactly as the (corrected) diagram depicts — no invented edges remain. |
| `README.md` / `docs/demo-script.md` | verified-working CLI commands | Textual citation | ✓ WIRED | All cited commands (`python3 -m scripts.run_demo ...`, `uvicorn api:app --reload`, `python3 -m pytest`) were executed live in this verification session and produced the exact documented output. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DEMO-02 | 07-01 | End-to-end run completes with no manual glue steps and repeats deterministically | ✓ SATISFIED (HTTP pipeline); extension-capture sub-clause is a documented Phase 4 dependency, not a code gap | Live pytest + live CLI runs, all passing |
| DEMO-03 | 07-02 | README documents setup and run instructions | ✓ SATISFIED | README.md read in full, sections present and accurate |
| DEMO-04 | 07-02 | An OSI license is present at the repo root | ✓ SATISFIED | LICENSE read in full, valid MIT text |
| DEMO-05 | 07-02 | Architecture diagram and demo script included | ✓ SATISFIED | docs/architecture.md + docs/demo-script.md read in full, cross-verified against real code, CR-01/IN-03 fixes confirmed applied |

No orphaned requirements: REQUIREMENTS.md maps only DEMO-02/03/04/05 to Phase 7 (confirmed via `grep -n "Phase 7" .planning/REQUIREMENTS.md`), and both plans' `requirements:` frontmatter fields together cover all four (07-01: [DEMO-02], 07-02: [DEMO-03, DEMO-04, DEMO-05]).

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in the phase's modified files. The code-review pass (07-REVIEW.md) already found and fixed the one substantive defect (CR-01, invented supervisor-convergence edges) and one weak-assertion pattern (WR-02, bare-substring README check) — both confirmed fixed and re-verified live in this session, not merely trusted from the SUMMARY.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green | `cd backend && python3 -m pytest -q` | 125 passed, 1 warning | ✓ PASS |
| Demo creep scenario | `cd backend && python3 -m scripts.run_demo --fixture creep` | exit 0, `ops_cards=2` | ✓ PASS |
| Demo clean scenario | `cd backend && python3 -m scripts.run_demo --fixture clean` | exit 0, `ops_cards=0` | ✓ PASS |
| Demo ambiguous scenario | `cd backend && python3 -m scripts.run_demo --ambiguous` | exit 0, `proposal=needs_human_input` | ✓ PASS |
| Determinism + presence + single-writer tests | `pytest tests/test_demo_determinism.py tests/test_submission_presence.py tests/test_single_writer.py -q` | 8 passed | ✓ PASS |
| No secrets/email leak | `grep -RniE "aws_secret_access_key\|aws_access_key_id\|ai@mainlandtech.com" README.md LICENSE docs/architecture.md docs/demo-script.md` | exit 1 (no match) | ✓ PASS |
| No store import in scripts/ | `grep -n "import store\|from store" backend/scripts/*.py` | no output | ✓ PASS |

### Human Verification Required

### 1. Extension-capture scope acknowledgment

**Test:** Confirm that Success Criterion 1's literal first hop ("extension capture") is acceptably scoped out as a Phase 4 dependency for this phase's "satisfies every submission requirement" claim.
**Expected:** The developer accepts that the demo's capture step is `POST /capture` called directly (exactly as the not-yet-built extension would call it), per README.md's "Manual-only boundaries" #1 and docs/architecture.md's dashed extension node.
**Why human:** This is a roadmap-sequencing/scope judgment, not a fact resolvable by reading code — the code itself is honest and consistent about this gap (dashed diagram node, explicit README callout), but whether that satisfies "every submission requirement" for judging purposes is a human call.

### 2. Recorded demo video

**Test:** Record the ≤5-minute walkthrough following docs/demo-script.md's four beats.
**Expected:** A video artifact exists.
**Why human:** Recording video is an explicit human action outside code-verification scope; this phase ships only the script, by design (README.md "Manual-only boundaries" #2).

### Gaps Summary

No code-level gaps found. All 8 code-verifiable must-haves (SC1's HTTP pipeline, SC2's determinism proof including the newly-added ambiguous-path test, SC3's README/LICENSE, and SC4's corrected architecture diagram + demo script) are VERIFIED against the actual codebase by live command execution and side-by-side code reading in this session — not by trusting SUMMARY.md or 07-REVIEW.md claims alone. The one prior code review (07-REVIEW.md) found one CRITICAL issue (CR-01: invented supervisor-convergence edges in the Mermaid diagram) and one weak-assertion WARNING (WR-02); both fixes were independently re-verified in this session by reading the current file state and re-running the corresponding tests/greps, not merely trusted from 07-REVIEW-FIX.md. Two items are routed to human_needed: the extension-capture scope question (a documented, non-code Phase 4 dependency) and the recorded video (an explicit human action). Neither is a BLOCKER against Phase 7's own deliverable scope as documented in this repo.

---

_Verified: 2026-09-09T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
