# Architecture

This diagram is grounded in the real `backend/` object graph — every symbol named below
exists in the code (verified by reading `backend/api.py`, `backend/agents/supervisor.py`,
`backend/agents/{triage_runner,proposal_runner,ops_runner}.py`, `backend/store/*.py`, and
`backend/fixtures/loader.py`). The Chrome MV3 extension is drawn dashed/planned because it
is a Phase 4 dependency that does not exist on this branch.

```mermaid
flowchart TD
    subgraph client_tier["Browser / Client (PLANNED — Phase 4, not on this branch)"]
        ext["Chrome MV3 extension<br/>popup.js / background.js"]
    end
    ext -.->|"POST /capture<br/>(planned)"| api

    demo["backend/scripts/run_demo.py<br/>(TestClient driver)"] -->|"in-process calls"| api

    subgraph api_tier["API / Backend — backend/api.py (sole EngagementStore writer, REC-03)"]
        api["FastAPI app"]
        cap["POST /capture"]
        getE["GET /engagements/{id}"]
        adv["POST /engagements/{id}/advance?stage=proposal|ops"]
        api --> cap
        api --> getE
        api --> adv
    end

    cap -->|"TriageRunner DI seam"| triage_runner["agents/triage_runner.py<br/>get_triage_runner()"]
    adv -->|"ProposalRunner DI seam"| proposal_runner["agents/proposal_runner.py<br/>get_proposal_runner()"]
    adv -->|"OpsRunner DI seam"| ops_runner["agents/ops_runner.py<br/>get_ops_runner()"]

    triage_runner -->|"default: TRIAGE_BACKEND=placeholder"| det_triage["_deterministic_triage_runner<br/>-> placeholder_kill_switch_check"]
    triage_runner -->|"TRIAGE_BACKEND=supervisor (manual-only)"| sup_triage["_supervisor_triage_runner<br/>-> build_supervisor()"]

    proposal_runner -->|"default: PROPOSAL_BACKEND=placeholder"| det_prop["_deterministic_proposal_runner<br/>-> check_scope_clarity / draft_proposal / draft_contract"]
    proposal_runner -->|"PROPOSAL_BACKEND=supervisor (manual-only)"| sup_prop["_supervisor_proposal_runner<br/>-> build_proposal_supervisor()"]

    ops_runner -->|"default: OPS_BACKEND=placeholder"| det_ops["_deterministic_ops_runner<br/>-> check_scope_creep / check_invoice_status / draft_status_update"]
    ops_runner -->|"OPS_BACKEND=supervisor (manual-only)"| sup_ops["_supervisor_ops_runner<br/>-> build_full_supervisor()"]

    sup_triage --> full_sup
    sup_prop --> full_sup
    sup_ops --> full_sup["agents/supervisor.py<br/>build_full_supervisor()<br/>(agents-as-tools, ORC-01)"]

    full_sup --> triage_agent["gig_triage_agent<br/>(agents/gig_triage_agent.py)"]
    full_sup --> prop_agent["proposal_contract_agent<br/>(agents/proposal_contract_agent.py)"]
    full_sup --> ops_agent["ops_agent<br/>(agents/ops_agent.py)"]

    triage_agent -.->|"live only"| bedrock["Amazon Bedrock<br/>(Claude, via BedrockModel)"]
    prop_agent -.->|"live only"| bedrock
    ops_agent -.->|"live only"| bedrock

    det_ops -->|"pure-data loader"| fixtures["fixtures/loader.py<br/>load_client_thread / load_payment_schedule"]

    cap --> store_write["store.create(record)"]
    adv --> store_write2["store.save(record)"]
    store_write --> store["store/engagement_store.py<br/>EngagementStore (ABC)"]
    store_write2 --> store
    store --> file_store["store/file_engagement_store.py<br/>FileEngagementStore<br/>(JSON files, data/engagements/)"]
```

## Component Table

| Component | File | Role |
|-----------|------|------|
| FastAPI app | `backend/api.py` | Exposes `/capture`, `GET /engagements/{id}`, `/advance?stage=proposal\|ops`; the **sole** `EngagementStore` writer (REC-03) |
| Demo driver | `backend/scripts/run_demo.py` | `TestClient(app)`-driven CLI that runs the full pipeline in-process, no live server, no AWS creds required |
| TriageRunner / ProposalRunner / OpsRunner | `backend/agents/{triage_runner,proposal_runner,ops_runner}.py` | Dependency-injection seams FastAPI calls; each has a deterministic default path and a `*_BACKEND=supervisor` live path |
| Supervisor | `backend/agents/supervisor.py` (`build_full_supervisor`) | Unified Strands Supervisor orchestrating all three specialists as agents-as-tools (ORC-01) — used by the live path only |
| Specialist agents | `agents/gig_triage_agent.py`, `agents/proposal_contract_agent.py`, `agents/ops_agent.py` | The three specialists the Supervisor wraps; reach Amazon Bedrock only on the live path |
| Fixture loader | `backend/fixtures/loader.py` | Pure-data loader (`load_client_thread`, `load_payment_schedule`) feeding the deterministic ops path |
| Persistence | `backend/store/engagement_store.py` (`EngagementStore` ABC), `backend/store/file_engagement_store.py` (`FileEngagementStore`) | The single persistence interface + its one concrete JSON-file implementation, written to only by `api.py` |
| Chrome MV3 extension | *(not on this branch — Phase 4)* | Planned real-world capture front that would POST to `/capture`; drawn dashed above |
