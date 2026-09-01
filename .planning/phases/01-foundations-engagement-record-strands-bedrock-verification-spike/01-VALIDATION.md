---
phase: "1"
slug: "foundations-engagement-record-strands-bedrock-verification-spike"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-01"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | backend/pyproject.toml (Wave 0 installs) |
| **Quick run command** | `cd backend && python -m pytest -q` |
| **Full suite command** | `cd backend && python -m pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest -q`
- **After every plan wave:** Run `cd backend && python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | — | — | N/A | unit | `cd backend && python -m pytest -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | REC-01 | — | N/A | unit | `cd backend && python -m pytest tests/test_engagement_record.py -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | REC-02 | — | N/A | unit | `cd backend && python -m pytest tests/test_store.py -q` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | REC-03 | — | store has exactly one writer path | unit | `cd backend && python -m pytest tests/test_single_writer.py -q` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 2 | ORC-03 | — | Bedrock smoke test fails fast + readably when creds/model absent | integration | `cd backend && python -m pytest tests/test_bedrock_smoke.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — pytest config + pinned deps (strands-agents, pydantic v2, boto3, fastapi)
- [ ] `backend/tests/conftest.py` — shared fixtures (tmp store dir)
- [ ] pytest install — if no framework detected

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Bedrock call returns a Claude completion | ORC-03 | Requires real AWS Bedrock creds + Claude model access, absent in this sandbox (placeholder creds) | With valid AWS creds + region set, run the Bedrock smoke script; expect a completion. Without them, expect a fast, readable error (the automated acceptance path). |
| Strands 2-agent trace shows distinct per-agent tool calls | ORC-03 | Exact trace attribute shape not confirmed against a live 1.54.0 run | Run the smoke script; inspect `agent.messages` / `result.metrics` for two distinct tool-call entries. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
