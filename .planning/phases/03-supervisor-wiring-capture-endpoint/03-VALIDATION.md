---
phase: "3"
slug: "supervisor-wiring-capture-endpoint"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-02"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + FastAPI TestClient (httpx) |
| **Config file** | backend/pyproject.toml (Phase 1) |
| **Quick run command** | `cd backend && python -m pytest -q` |
| **Full suite command** | `cd backend && python -m pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest -q`
- **After every plan wave:** `cd backend && python -m pytest`
- **Before `/gsd-verify-work`:** Full suite green.
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | ORC-02 | — | placeholder triage returns typed TriageSlice via a plain function (no LLM) | unit | `cd backend && python -m pytest tests/test_triage_runner.py -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | ORC-02 | — | Supervisor + distinct triage specialist Agent construct; specialist registered as a tool | unit | `cd backend && python -m pytest tests/test_supervisor_wiring.py -q` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 2 | API-01 | T-03-01 | POST /capture creates a record, merges typed triage verbatim, persists, returns verdict (offline placeholder path) | integration | `cd backend && python -m pytest tests/test_capture_endpoint.py -q` | ❌ W0 | ⬜ pending |
| 3-01-04 | 01 | 2 | API-02 | — | GET /engagements/{id} returns the persisted record; 404 on unknown | integration | `cd backend && python -m pytest tests/test_engagements_endpoint.py -q` | ❌ W0 | ⬜ pending |
| 3-01-05 | 01 | 2 | API-01 | T-03-02 | /capture fails fast + readable (503, no credential leak, no raw traceback) when the live Bedrock backend is selected without creds | integration | `cd backend && python -m pytest tests/test_capture_bedrock_failfast.py -q` | ❌ W0 | ⬜ pending |
| 3-01-06 | 01 | 2 | REC-03 | — | api module is the only writer; agents/tools still import no store (existing single-writer test still passes) | unit | `cd backend && python -m pytest tests/test_single_writer.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — add fastapi, httpx (if not already present from Phase 1 deps)
- [ ] `backend/tests/conftest.py` — TestClient + tmp-store fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live two-Agent trace (Supervisor + triage) via real Bedrock | ORC-02 / success criterion 4 | Requires real AWS Bedrock creds absent in sandbox (placeholder) | With real creds + region and TRIAGE_BACKEND=live, POST /capture and inspect `supervisor.messages` for two distinct Agent invocations + the specialist's `{"json":...}` toolResult block. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
