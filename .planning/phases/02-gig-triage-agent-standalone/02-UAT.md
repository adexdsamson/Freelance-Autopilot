---
status: paused
phase: 02-gig-triage-agent-standalone
source: [02-SUMMARY.md]
started: 2026-09-03T00:00:00Z
updated: 2026-09-09T00:00:00Z
---

## Current Test

number: 6
name: Missing AWS credentials fail readably, never as a traceback
expected: |
  From backend/, with credentials forced off:

      env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_PROFILE \
        AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
        .venv/bin/python -m scripts.run_triage strong_fixed_apply; echo "exit: $?"

  Prints ONE line starting "FAIL: triage could not complete
  (NoCredentialsError)" that points at the Bedrock smoke test,
  then "exit: 1".

  No Python traceback, and no raw AWS error text -- the exception
  type name is all that is ever printed (T-02-01).
awaiting: paused at test 6 — user moved to Phase 4 work on 2026-09-09

## Tests

### 1. Automated test suite passes
expected: `cd backend && .venv/bin/python -m pytest -q` ends with `106 passed`, no failures or errors.
result: pass

### 2. Underpriced job is rejected without needing AWS credentials
expected: `.venv/bin/python -m scripts.run_triage below_budget_floor` prints JSON with `"verdict": "skip"`, `"score": 0.0`, and reasoning naming the $500 floor. Completes instantly with no AWS call.
result: pass

### 3. Red-flag phrase disqualifies an otherwise-strong job
expected: `.venv/bin/python -m scripts.run_triage red_flag_unpaid_test` returns `"verdict": "skip"` and reasoning naming `'unpaid test'` — despite the posting having a $6,000 budget and a verified client at a 66% hire rate.
result: pass

### 4. Weak client history disqualifies with both reasons named
expected: `.venv/bin/python -m scripts.run_triage weak_client_stats` returns `"verdict": "skip"` with reasoning naming BOTH the $180 spend and the 11% hire rate, and `extracted_fields.budget` is 4200.0 (the job budget, not the client's spend).
result: pass

### 5. Gate decisions are byte-identical across repeated runs
expected: Running the same gate-rejected fixture three times produces identical output each time (DEMO-02 in miniature). Suggested check:
  `for i in 1 2 3; do .venv/bin/python -m scripts.run_triage below_budget_floor; done | sort -u | wc -l` — the three runs collapse to one unique body (18 distinct lines).
result: pass

### 6. Missing AWS credentials fail readably, never as a traceback
expected: With credentials unset, `.venv/bin/python -m scripts.run_triage strong_fixed_apply` prints a single `FAIL: triage could not complete (NoCredentialsError)...` line pointing at the Bedrock smoke test, exits 1, and shows no Python traceback and no AWS error text.
result: [pending]

### 7. A strong job reaches Bedrock and returns an apply verdict
expected: With real AWS credentials, `.venv/bin/python -m scripts.run_triage strong_fixed_apply` returns `"verdict": "apply"` with a score above 60 and reasoning naming fit, competition and rate sub-scores. This is the one path never yet run live.
result: [pending]

### 8. A thin-but-viable client is flagged and weighed, not silently killed
expected: With credentials, `.venv/bin/python -m scripts.run_triage thin_client_flagged` returns a scored verdict (not a pre-screen skip), and the reasoning ends with a "Pre-screen concerns weighed:" sentence naming the thin spend and weak hire rate.
result: [pending]

### 9. Your own real job posting parses correctly
expected: Save a real job posting you would actually consider into a file, then run `.venv/bin/python -m scripts.run_triage --file /path/to/posting.txt`. The `extracted_fields` show the correct title, the correct budget with the right `budget_type` (fixed vs hourly), and correct client stats. This is the test the fixtures cannot do for you — it is real-world text the parser has never seen.
result: [pending]

## Summary

total: 9
passed: 5
issues: 0
pending: 4
skipped: 0

## Gaps

[none yet — tests 1-5 all passed]

## Paused

Paused 2026-09-09 at test 6 of 9. Tests 1-5 passed (suite, budget floor,
red-flag phrase, weak client with correct budget parse, determinism).

Outstanding:
- Test 6 — no-credential failure is readable (runnable now, no AWS needed)
- Test 7 — strong job scores + returns apply (**needs live AWS credentials**)
- Test 8 — thin client flagged not killed (**needs live AWS credentials**)
- Test 9 — a real pasted posting parses correctly (needs a real posting)

Tests 7 and 8 are the only verification that `llm_scorecard` works against
real Bedrock. Until they run, that path remains unproven — see STATE.md
blockers.
