# Phase 3: Supervisor Wiring + /capture — Discussion Log

**Mode:** --only 3 autonomous (auto; recommended options selected, grounded in research + the Phase-2-not-built constraint)
**Date:** 2026-09-01

Auto-selected decisions:

| Area | Decision | Basis |
|------|----------|-------|
| Agents-as-tools wiring | Supervisor + distinct Gig Triage specialist Agent via @tool | STACK.md §2; success criterion 4 |
| Typed merge (ORC-02) | Specialist returns typed TriageResult; FastAPI merges verbatim | ARCHITECTURE.md; criterion 3 |
| Phase 2 gap | Deterministic placeholder triage behind a stable seam; Phase 2 fills it | user chose --only 3; two-engineer split |
| Sole writer | /capture is the only create+save path; store injected | REC-03; Phase 1 |
| Credential-less tests | Offline tests drive the seam deterministically; live Bedrock orchestration is manual | Phase 1 precedent; sandbox placeholder creds |

## Deferred
- Real triage tools -> Phase 2 (Engineer B).
- /advance (proposal/ops) -> Phase 5/6.
