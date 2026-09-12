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
env-var switch. A Manifest V3 Chrome extension ([`extension/`](extension/)) is the
paste-based capture front that POSTs a job posting to `/capture`. Persistence sits behind a
swappable `EngagementStore` interface: a file-based store by default, with an optional
Amazon Bedrock AgentCore Memory store and Runtime entrypoint selectable by config. See
[`docs/architecture.md`](docs/architecture.md) for the full Mermaid diagram and component
table.

### Layout

- `backend/` — FastAPI app, the Strands Supervisor + three specialist agents, tools,
  fixtures, the Engagement Record store, and the test suite.
- `extension/` — the Manifest V3 capture extension (popup + background service worker) and
  a local stub `/capture` server for development.
- `docs/` — architecture diagram and the demo-walkthrough script.

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

### Chrome extension (capture front)

The extension is loaded unpacked in Chrome:

1. Start the backend (`cd backend && uvicorn api:app --reload`), or the lightweight stub
   (`python3 extension/dev/stub_capture_server.py`) for UI-only work.
2. Open `chrome://extensions`, enable **Developer mode**, choose **Load unpacked**, and
   select the [`extension/`](extension/) directory.
3. Open the popup, paste a job posting, and submit; the triage verdict, score, and
   reasoning render inline once `/capture` responds.

`host_permissions` is scoped to the local backend origin only (no `<all_urls>`). See
[`extension/README.md`](extension/README.md) for details.

## Optional: AgentCore deployment

The Engagement Record store is swappable behind the `EngagementStore` interface. An
optional Amazon Bedrock AgentCore Memory store (`backend/store/agentcore_memory_store.py`,
selected via `backend/store/factory.py`) and a Runtime entrypoint
(`backend/agentcore_runtime.py`) let the Supervisor and specialists run on AgentCore
without changing agent or API code. This path is off by default; the file-based store is the
supported default and the offline demo never requires it. Install the optional dependency
with:

```bash
pip install './backend[agentcore]'   # or: pip install 'bedrock-agentcore[strands-agents]'
```

The live AgentCore Memory round trip and Runtime deployment need real AWS credentials and a
provisioned AgentCore Memory resource; they are manual-verification-only (see below).

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
| CAP-01..03 | Manifest V3 paste-based capture extension posts to `/capture` and renders the verdict inline | Complete (Phase 4, [`extension/`](extension/)) |
| DEPLOY-01/02 (v2) | Optional AgentCore Memory store + Runtime behind the store interface | Present, off by default (Phase 8) |

All v1 requirements (Phases 1–7) are complete and merged. See
[`.planning/REQUIREMENTS.md`](.planning/REQUIREMENTS.md) for the full requirements list.

## Manual-only boundaries

These things are intentionally out of scope for automation in this repository:

1. **The live extension round trip in a browser.** The Manifest V3 extension is built
   ([`extension/`](extension/)) and its structure is covered by tests, but exercising the
   real popup -> service-worker -> `/capture` round trip requires loading it unpacked in
   Chrome against a running backend — a manual step. The one-command demo drives the same
   `POST /capture` call the extension makes, so the pipeline is exercised end to end without
   a browser.
2. **The recorded demo video.** This repository ships the walkthrough script
   ([`docs/demo-script.md`](docs/demo-script.md)) the video follows; recording the video
   itself is a human action.
3. **The live four-agent Bedrock trace.** By default every stage runs deterministic
   placeholder logic offline. To exercise the real Supervisor -> specialist agents against
   Amazon Bedrock, configure AWS credentials via the standard boto3 chain and export
   `TRIAGE_BACKEND=supervisor`, `PROPOSAL_BACKEND=supervisor`, and `OPS_BACKEND=supervisor`
   before running the demo or server commands above. This path is manual-verification-only
   and is never exercised by the automated test suite.
4. **The live AgentCore Memory / Runtime path.** The optional store and Runtime entrypoint
   are present (see "Optional: AgentCore deployment") but the live round trip and deployment
   need real AWS credentials and a provisioned AgentCore Memory resource; they are
   manual-verification-only and never exercised by the automated test suite.
