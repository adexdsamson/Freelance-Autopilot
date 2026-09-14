---
status: testing
scope: cross-phase manual verification (submission readiness)
started: 2026-09-14
updated: 2026-09-14
---

# Human Verification — Freelance Autopilot

The deterministic/offline side is fully green and re-verified live on `main`:

- `cd backend && python3 -m pytest` → 240 passed, 1 skipped (AgentCore adapter, optional dep absent)
- `run_demo --fixture creep` → apply, 2 ops cards
- `run_demo --fixture clean` → apply, 0 ops cards
- `run_demo --ambiguous` → needs_human_input escalation, ops skipped

The items below cannot be verified in the build sandbox (no real AWS credentials,
no browser, no recording). They require a human on a machine with those resources.

## Checks

### 1. Live four-agent Bedrock trace  (ORC-01, ORC-03 — Phases 1/3/5/6)
steps: |
  Configure real AWS credentials via the standard boto3 chain (env vars, shared
  profile, or instance role) for a region with the pinned Claude model enabled.
  Then:
    cd backend
    export TRIAGE_BACKEND=supervisor PROPOSAL_BACKEND=supervisor OPS_BACKEND=supervisor
    python3 -m scripts.run_demo --fixture creep
expected: |
  The pipeline completes against real Bedrock with the same decision outcomes as
  the deterministic run (apply -> proposal/contract -> 2 ops cards), and the run's
  trace/telemetry shows FOUR distinct Agent invocations — Supervisor plus the Gig
  Triage, Proposal-Contract, and Ops specialists — not one flat call. On a bad
  credential/model, it fails fast with a readable 503 and no credential value is
  printed.
result: [pending]

### 2. Extension live round-trip in Chrome  (CAP-02 — Phase 4)
steps: |
  Start the backend:  cd backend && uvicorn api:app
  In Chrome: chrome://extensions -> enable Developer mode -> Load unpacked ->
  select the extension/ directory. Close DevTools and leave it idle >30s so the
  service worker cold-starts. Open the popup, paste a job posting, submit.
expected: |
  The popup shows an explicit pending state, then renders the returned verdict,
  score, and reasoning inline once /capture responds — completing the round trip
  after a cold start.
result: [pending]

### 3. Live AgentCore Memory round-trip + Runtime  (DEPLOY-01/02 — Phase 8, OPTIONAL)
steps: |
  Optional / cut-first stretch. Install the extra (pip install './backend[agentcore]'),
  provision an AgentCore Memory resource, select the AgentCore store via the store
  factory config, and run a capture -> advance flow (optionally deployed to AgentCore
  Runtime).
expected: |
  The Engagement Record persists and reloads through AgentCore Memory with no change
  to agent or API code, and the file-based path still works end to end as the fallback.
result: [pending]

### 4. Recorded <=5-minute demo video  (Phase 7 submission)
steps: |
  Follow docs/demo-script.md and record the walkthrough.
expected: |
  A <=5-minute recording that follows the script: creep -> 2 ops cards, clean -> 0,
  ambiguous -> needs_human_input, plus the manual live-Bedrock note.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
