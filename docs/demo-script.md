# Demo Script (≤5 minutes)

A recorded-walkthrough script for a judge/viewer. Every beat runs a real, verified command
against `backend/scripts/run_demo.py` — nothing here is narrated over a mock. Run all
commands from the repository root with `cd backend &&` prefixed, or start a shell already
in `backend/`.

Out of scope for this script: the Chrome MV3 extension capture front (a Phase 4
dependency, not built on this branch — the `POST /capture` call below is exactly what the
extension would itself make) and the recording of the video itself (a human action this
script exists to support, not replace).

## Beat 1 — Creep fixture: full pipeline, 2 ops escalation cards (~90s)

```bash
cd backend && python3 -m scripts.run_demo --fixture creep
```

Narrate as it prints:
1. **Capture**: the job is triaged and the console prints the `apply` verdict, score, and
   reasoning.
2. **Proposal**: a phased proposal and a signed SOW contract with a payment schedule are
   drafted and printed.
3. **Ops**: the console prints the ops escalation output — a scope-creep flag (the client
   thread contains a message asking for extra work outside the signed SOW) and an overdue
   invoice flag (one milestone is past its due date in the fixture payment schedule), for
   a total of **2 ops escalation cards**. The final `SUMMARY ... ops_cards=2` line
   confirms this count.

## Beat 2 — Clean fixture: 0 ops cards proves the checks are conditional (~60s)

```bash
cd backend && python3 -m scripts.run_demo --fixture clean
```

Narrate: the same pipeline runs against the "clean" client-thread and payment-schedule
fixtures — no scope-creep message, no overdue milestone — so the ops stage produces
**0 escalation cards**. The final `SUMMARY ... ops_cards=0` line proves the scope-creep and
invoice checks are genuinely conditional on the input data, not hardcoded to always fire.

## Beat 3 — Ambiguous scope: proposal-stage escalation (~60s)

```bash
cd backend && python3 -m scripts.run_demo --ambiguous
```

Narrate: this run submits a deliberately ambiguous job ("Looking for someone to help with
ongoing design work.") that has no clear scope or timeline. Instead of guessing, the
Proposal-Contract stage escalates with `needs_human_input=True` and a specific
clarifying `question` — no contract is drafted, and the ops stage is skipped entirely
because there is no signed contract to run ops checks against. The final
`SUMMARY scenario=ambiguous ... proposal=needs_human_input` line confirms this.

## Beat 4 — Live Bedrock trace (manual step, not recorded by default)

Everything above runs the deterministic default backends — fully offline, no AWS
credentials needed. To additionally show the real Supervisor-routed specialist agents on
Bedrock, configure AWS credentials via the standard boto3 chain and export:

```bash
export TRIAGE_BACKEND=supervisor
export PROPOSAL_BACKEND=supervisor
export OPS_BACKEND=supervisor
```

Then re-run any of the beats above (e.g. `cd backend && python3 -m scripts.run_demo
--fixture creep`) to exercise the same pipeline against live Amazon Bedrock. Each stage
independently routes through its own stage-scoped Supervisor: the triage stage's
`build_supervisor()` and the proposal stage's `build_proposal_supervisor()` each wrap only
their own single specialist, and only the ops stage's Supervisor (`build_full_supervisor()`)
has all three specialists registered as tools — though its system prompt still restricts it
to calling exactly one specialist tool per turn, so no single advance ever invokes more than
one specialist. This mirrors the connectivity check in
`backend/scripts/smoke_test_bedrock_connectivity.py`. This step is manual-verification-only
and is never exercised by the automated test suite — no credential literal is required or
referenced by this script.

## Wrap-up (~30s)

Recap: one command each for a full apply-and-escalate run, a clean run proving the checks
are conditional, and an ambiguous-scope escalation — all deterministic, offline, and
reproducible via `cd backend && python3 -m pytest`.
