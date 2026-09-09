# Freelance Autopilot

An agentic system that owns a freelance engagement end to end: deciding whether a gig is
worth applying to, drafting the proposal and contract, and running lightweight ops
(status updates, scope-creep detection, invoice tracking) once the engagement is live —
orchestrated by a Strands Agents SDK Supervisor over three specialist agents. A hackathon
submission for the "Agents for Humans" (AWS Strands Agents SDK) Professional Agents track.

## Architecture

A FastAPI backend is the sole writer of the Engagement Record; it exposes `/capture`,
`GET /engagements/{id}`, and `/advance?stage=proposal|ops` and drives a unified Strands
Supervisor (`build_full_supervisor`) that orchestrates the Gig Triage, Proposal-Contract,
and Ops specialist agents via the agents-as-tools pattern. Each stage has a deterministic
default backend for the demo and a live Bedrock path behind a `*_BACKEND=supervisor`
env-var switch. See [`docs/architecture.md`](docs/architecture.md) for the full Mermaid
diagram and component table.

## Setup

- Python 3.10+ (verified against 3.11.15).
- Install dependencies:

  ```bash
  pip install -r backend/requirements.txt
  ```

- The deterministic demo path (default) requires **no AWS credentials** — every stage runs
  fully offline against pure-Python placeholder logic and bundled fixtures.
- The optional **live** four-agent Bedrock path (see "Manual-only boundaries" below) needs
  AWS credentials configured via the standard boto3 credential chain (environment
  variables, shared config/profile, or an instance role — no Strands-specific credential
  mechanism exists). Configure credentials however you normally do for AWS; nothing here
  requires printing or storing a key in the repo.

## Run

Run the full deterministic demo pipeline (capture -> proposal -> ops) in one command, with
no manual glue steps:

```bash
cd backend && python3 -m scripts.run_demo --fixture creep
```

Other scenarios:

```bash
cd backend && python3 -m scripts.run_demo --fixture clean
cd backend && python3 -m scripts.run_demo --ambiguous
```

Start the FastAPI server directly (for interactive/manual exploration):

```bash
cd backend && uvicorn api:app --reload
```

> Note: both commands must be run with `backend/` as the working directory —
> `backend/api.py`'s imports are bare-name (`from agents...`, `from models...`) and only
> resolve when `backend/` itself is on `sys.path`. The forms `python3
> backend/scripts/run_demo.py` and `uvicorn backend/api.py:app` do **not** work.

## Test

Run the full offline test suite (no AWS credentials required):

```bash
cd backend && python3 -m pytest
```

## Requirements Traceability

| Requirement | Description | Status |
|-------------|-------------|--------|
| DEMO-02 | Deterministic end-to-end demo run, no manual glue steps | Complete (Phase 7) |
| DEMO-03 | README documents setup and run instructions | Complete (Phase 7, this file) |
| DEMO-04 | An OSI license is present at the repo root | Complete (Phase 7, [`LICENSE`](LICENSE)) |
| DEMO-05 | An architecture diagram and a demo script are included | Complete (Phase 7, [`docs/architecture.md`](docs/architecture.md), [`docs/demo-script.md`](docs/demo-script.md)) |
| ORC-01 | Supervisor orchestrates three specialist agents via agents-as-tools | Complete (Phase 6) |
| ORC-02 | Each specialist returns strict typed JSON merged verbatim, never re-authored | Complete (Phase 3) |
| REC-03 | FastAPI is the sole writer that merges specialist output into the Engagement Record | Complete (Phase 1) |
| API-03 | `POST /engagements/{id}/advance` advances the engagement to the next stage | Complete (Phase 6) |

See [`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) for the full requirements list.

## Manual-only boundaries

Three things are intentionally out of scope for automation in this repository:

1. **Chrome MV3 extension capture front.** The extension that would paste a job posting
   and POST it to `/capture` is a Phase 4 dependency and is not built on this branch. The
   "capture" step in the demo is the same `POST /capture` call the extension would itself
   make; nothing here is faked, it's simply not yet wired to a browser UI.
2. **The recorded demo video.** This repository ships the walkthrough script
   ([`docs/demo-script.md`](docs/demo-script.md)) the video follows; recording the video
   itself is a human action.
3. **The live four-agent Bedrock trace.** By default every stage runs deterministic
   placeholder logic offline. To exercise the real Supervisor -> specialist agents against
   Amazon Bedrock, configure AWS credentials via the standard boto3 chain and export
   `TRIAGE_BACKEND=supervisor`, `PROPOSAL_BACKEND=supervisor`, and `OPS_BACKEND=supervisor`
   before running the demo or server commands above. This path is manual-verification-only
   and is never exercised by the automated test suite.
