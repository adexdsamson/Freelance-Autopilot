---
phase: "5"
slug: "proposal-contract-agent-advance-stage-proposal"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-05"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Phase 1/3 suite; FastAPI `TestClient`/`httpx`) |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python3 -m pytest -q` |
| **Full suite command** | `cd backend && python3 -m pytest` |
| **Estimated runtime** | ~5 seconds (37 tests green at Phase 3 baseline; no live Bedrock) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python3 -m pytest -q`
- **After every plan wave:** Run `cd backend && python3 -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

*Seeded by the planner (draft). The plan's per-task `<verify><automated>` commands are the source of truth; this table is filled during execution.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | — | PROP-01..04 | T-05-* / — | See plan `<threat_model>` | unit/api | `cd backend && python3 -m pytest -q` | ✅ (existing infra) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure (pytest + `backend/tests/conftest.py` + FastAPI `TestClient`) covers all Phase 5 requirements. No new framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live two-agent Bedrock trace (Supervisor → Proposal-Contract specialist), `PROPOSAL_BACKEND=supervisor` | PROP-01..04 (live path) | Requires real AWS/Bedrock credentials; sandbox has placeholder creds | Export real AWS creds + region, set `PROPOSAL_BACKEND=supervisor`, POST `/engagements/{id}/advance` for an apply engagement, inspect the two distinct Agent invocations in the trace |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
