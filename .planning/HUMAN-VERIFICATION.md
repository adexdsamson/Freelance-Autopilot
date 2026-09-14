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
result: partial
notes: |
  Progress on Windows (2026-09-14):
  - Fail-fast half VERIFIED: with no AWS credentials, STEP 1 returned
    `503: {"detail":"no AWS credentials found for Bedrock."}` — readable,
    credential-free fail-fast (ORC-03).
  - With valid AWS credentials the app authenticated and reached Bedrock. The
    live trace showed the Supervisor invoking the specialist as a tool
    (`Tool #1: gig_triage_agent, tool_use_id=<tooluse_...>`) — real agents-as-tools
    orchestration (ORC-01/ORC-02) executing against Bedrock.
  - Remaining blocker is an AWS ACCOUNT step, not code: Bedrock returned
    ResourceNotFoundException "Model use case details have not been submitted for
    this account. Fill out the Anthropic use case details form before using the
    model." The app mapped it to a clean 503 with no credential leak. Complete the
    Anthropic use-case form in Bedrock Model access (us-east-1), wait ~15 min, retry.
  - Region/model resolved (2026-09-14): with AWS_REGION=ca-central-1 and a
    `global.anthropic.claude-sonnet-4-5-...` inference profile, Bedrock accepted the
    model and streamed a real Claude completion ("I'll analyze this job posting to
    determine whether you should apply or skip it."). The live trace showed the
    nested orchestration: Supervisor -> gig_triage_agent (tool) -> its own
    placeholder_kill_switch_check tool — agents-as-tools executing against real
    Bedrock (ORC-01/ORC-02 demonstrated live).
  - SOLE remaining gate is an AWS ACCOUNT onboarding step: "Model use case details
    have not been submitted for this account. Fill out the Anthropic use case
    details form ... try again in 15 minutes." Submit the Anthropic use-case form in
    Bedrock Model access, wait ~15 min, retry the same command for the full green run.
  - SECURITY: the AWS key used was exposed in a screenshot during testing and must
    be rotated/deleted.

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
result: pass
verified: 2026-09-14
notes: |
  Live round-trip CONFIRMED in Chrome on the offline placeholder path. Paste ->
  submit rendered the verdict inline: SKIP, Score 0.1/100, reasoning "budget 25.0
  is below the placeholder floor (100.0) — kill-switch rule fired", plus the
  extracted Engagement id — exactly the CAP-02/CAP-03 contract, after an MV3
  cold start.
  Two defects were found and fixed en route to this pass:
  - 422 "Field required: body.title": the extension posts { raw_text } but the
    original /capture required a structured JobSlice. Resolved by the dedicated
    POST /capture/text endpoint (deterministic extract_job_fields, TRI-01) that
    the extension's background.js now targets — landed in the
    gsd/phase-04.1-screenshot-capture merge (00158cb). (An alternative PR #9 that
    widened /capture itself was closed as superseded.)
  - Paste draft lost whenever the popup lost focus (MV3 tears the popup document
    down on blur — e.g. switching windows to copy the job URL). Fixed by mirroring
    the job-text/URL fields to localStorage on input and restoring them on reopen;
    localStorage needs no manifest permission, so the empty `permissions` posture
    (test_extension_manifest.py) is intact (PR #10, merged, commit fa6a181).
  Screenshot mode (POST /capture/screenshots) is a vision call and still needs
  live Bedrock, so it shares Check 1's account gate; paste mode is the offline
  demo path and is fully verified here.

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
passed: 1
partial: 1
issues: 0
pending: 2
