---
phase: "7"
slug: "full-demo-verification-submission-docs"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-09"
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from 07-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (config in `backend/pyproject.toml`, `[tool.pytest.ini_options] pythonpath=["."]`) |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && python3 -m pytest -q` |
| **Full suite command** | `cd backend && python3 -m pytest` |
| **Estimated runtime** | ~5 seconds (deterministic, offline — no Bedrock) |

---

## Sampling Rate

- **After every task commit:** `cd backend && python3 -m pytest -q`
- **After every plan wave:** `cd backend && python3 -m pytest`
- **Before `/gsd-verify-work`:** full suite green (118 existing + new tests)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | DEMO-02/SC1 | demo driver advances one record capture→proposal→ops via TestClient (no store import) | integration | `cd backend && python3 -m pytest tests/test_demo_determinism.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DEMO-02/SC2 | full fixture set 3× → identical decision fields (excl. engagement_id, invoice_flags[].days_overdue) | integration | `cd backend && python3 -m pytest tests/test_demo_determinism.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DEMO-03/SC3 | repo-root README.md present with required sections | presence | `cd backend && python3 -m pytest tests/test_submission_presence.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DEMO-05/SC3 | repo-root LICENSE present, OSI (MIT) text | presence | `cd backend && python3 -m pytest tests/test_submission_presence.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | DEMO-04/SC4 | docs/architecture.md (mermaid) + docs/demo-script.md present | presence | `cd backend && python3 -m pytest tests/test_submission_presence.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Requirement labels map by CONTENT — REQUIREMENTS.md has DEMO-04 (diagram+script) / DEMO-05 (license); CONTEXT.md's numeral labels are swapped. Follow REQUIREMENTS.md.*

---

## Wave 0 Requirements

- [ ] `backend/scripts/run_demo.py` — demo entrypoint (D-01); run via `cd backend && python3 -m scripts.run_demo`
- [ ] `backend/tests/test_demo_determinism.py` — DEMO-02/SC1+SC2 (3× identical, excl. UUID + days_overdue)
- [ ] `backend/tests/test_submission_presence.py` — DEMO-03/04/05 presence (path resolves to TRUE repo root — one extra `.parent` beyond test_single_writer.py's `backend/`)
- [ ] `README.md` (repo root) — DEMO-03; commands: `cd backend && python3 -m scripts.run_demo`, `cd backend && uvicorn api:app`, `cd backend && python3 -m pytest`
- [ ] `LICENSE` (repo root) — DEMO-05 (MIT; copyright holder user-adjustable, no email)
- [ ] `docs/architecture.md` — DEMO-04 (Mermaid, real object graph)
- [ ] `docs/demo-script.md` — DEMO-04 (≤5-min walkthrough tied to run_demo)
- [ ] No new framework/package install — pytest already configured; 118 tests green

---

## Manual-Only / Out-of-Scope Verifications

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Real Chrome-extension capture front driving `/capture` | SC1 (Phase 4 dep) | Extension not built on any branch (Phase 4) | Documented as a Phase 4 dependency; the demo posts what the extension would, via `/capture` |
| The recorded ≤5-minute demo video | submission | A human records it | This phase ships `docs/demo-script.md` (the script it follows), not the video |
| Live four-agent Bedrock trace | ORC-01/SC (prior phases) | Needs real AWS creds; sandbox has placeholders | Set creds + `*_BACKEND=supervisor`, run the flow (same precedent as Phases 1/3/5/6) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
