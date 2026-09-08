---
phase: "6"
slug: "ops-agent-fixtures-full-supervisor-wiring"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-08"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from 06-RESEARCH.md §Validation Architecture. The planner/executor refine the
> Per-Task Verification Map as PLAN.md tasks are authored.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (installed; verified `pip3 show pytest`) |
| **Config file** | none — pytest default discovery (mirrors Phase 3/5; no `pytest.ini`/`[tool.pytest]`) |
| **Quick run command** | `cd backend && python -m pytest tests/test_ops_tools.py tests/test_ops_runner.py -x` |
| **Full suite command** | `cd backend && python -m pytest` |
| **Estimated runtime** | ~10 seconds (deterministic, offline — no Bedrock) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_ops_tools.py tests/test_ops_runner.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | ORC-01 | — | build_full_supervisor registers 3 tools, 4 distinct Agents | unit | `cd backend && python -m pytest tests/test_full_supervisor_wiring.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | OPS-01 | — | check_scope_creep flags creep, none on clean | unit | `cd backend && python -m pytest tests/test_ops_tools.py -k scope_creep -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | OPS-02 | — | check_invoice_status flags overdue, none on clean | unit | `cd backend && python -m pytest tests/test_ops_tools.py -k invoice_status -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | OPS-03/SC4 | — | draft_status_update reflects active flags | unit | `cd backend && python -m pytest tests/test_ops_tools.py -k status_update -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | OPS-04/SC2 | — | creep+overdue → exactly 2 escalation cards | integration | `cd backend && python -m pytest tests/test_ops_runner.py -k creep -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | OPS-04/SC3 | — | clean → 0 escalation cards (conditional, not hardcoded) | integration | `cd backend && python -m pytest tests/test_ops_runner.py -k clean -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | API-03/SC5 | — | /advance routes+completes proposal AND ops | e2e | `cd backend && python -m pytest tests/test_advance_endpoint.py -k ops -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | API-03 | T-06-PT | ops precondition (no contract) → 4xx | e2e | `cd backend && python -m pytest tests/test_advance_endpoint.py -k precondition -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | REC-03 | T-06-STORE | ops agents/tools never import store | static (AST) | `cd backend && python -m pytest tests/test_single_writer.py -x` | ✅ existing | ⬜ pending |
| TBD | TBD | — | D-08(g) | T-06-LEAK | /advance ops fails fast + readable 503 | e2e | `cd backend && python -m pytest tests/test_advance_bedrock_failfast.py -k ops -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DEMO-01 | T-06-PT | fixtures loadable; variant selector produces two states | unit | `cd backend && python -m pytest tests/test_fixtures_loader.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_full_supervisor_wiring.py` — ORC-01 construction assertions (3 tools, 4 distinct Agents)
- [ ] `tests/test_ops_tools.py` — OPS-01/02/03 tool-level behavior
- [ ] `tests/test_ops_runner.py` — D-03 runner seam, SC2 (2 cards), SC3 (0 cards)
- [ ] `tests/test_fixtures_loader.py` — DEMO-01 loader + variant selector
- [ ] Extend `tests/test_advance_endpoint.py` — API-03/SC5 both stages, ops-precondition 4xx guard
- [ ] Extend `tests/test_advance_bedrock_failfast.py` — D-08(g) 503 fail-fast for the ops branch
- [ ] No new framework install — pytest already configured and passing (Phase 1/3/5 precedent)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live four-agent Bedrock trace shows four independently traceable invocations | ORC-01/SC1 | Requires real AWS Bedrock credentials; sandbox has placeholder creds | Set real creds + `OPS_BACKEND=supervisor`, run the full capture→proposal→ops flow, inspect the supervisor trace for four distinct Agent invocations (same precedent as Phases 1/3/5) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
