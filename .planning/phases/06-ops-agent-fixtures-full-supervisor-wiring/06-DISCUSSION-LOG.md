# Phase 6: Ops Agent, Fixtures & Full Supervisor Wiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 6-Ops Agent, Fixtures & Full Supervisor Wiring
**Mode:** `--auto` (fully autonomous discuss; recommended option auto-selected per area, no interactive prompts)
**Areas discussed:** Supervisor unification (ORC-01), Ops tools & determinism, OpsRunner seam, Fixtures & variants, /advance ops routing, Escalation cards

---

## Supervisor unification (ORC-01, SC1)

| Option | Description | Selected |
|--------|-------------|----------|
| New `build_full_supervisor` (all 3 tools), keep stage-scoped ones | Unified supervisor for ORC-01 + live path; name-disambiguated extraction | ✓ |
| Extend `build_supervisor` to 3 tools in place | Mutates the Phase-3 builder | |
| Skip unification, keep only stage-scoped supervisors | Fails SC1/ORC-01 | |

**Auto-selected:** New unified `build_full_supervisor` + name-disambiguated extractor (recommended default). → D-01.

---

## Ops tools & determinism (PRD §7.3)

| Option | Description | Selected |
|--------|-------------|----------|
| Three §7.3 dual-use `@tool`s, deterministic bodies | `check_scope_creep`/`check_invoice_status`/`draft_status_update`, no store import | ✓ |
| LLM-only ops generation | No deterministic bodies | |

**Auto-selected:** Three §7.3 dual-use tools, deterministic bodies (recommended default). → D-02.

---

## OpsRunner seam

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic default + `OPS_BACKEND` live path | Mirror TriageRunner/ProposalRunner | ✓ |
| Live Bedrock only / deterministic only | | |

**Auto-selected:** Deterministic default + env-selected live path (recommended default). → D-03.

---

## Fixtures & variants (DEMO-01, PRD §10)

| Option | Description | Selected |
|--------|-------------|----------|
| creep + clean variants (thread + schedule) + sample jobs | Drives SC2 (2 cards) vs SC3 (0 cards) deterministically | ✓ |
| Single fixture only | Can't prove conditional (SC3) | |

**Auto-selected:** creep + clean variants + sample jobs, with a variant selector (recommended default). → D-04.

---

## `/advance` ops routing (API-03, SC5)

| Option | Description | Selected |
|--------|-------------|----------|
| Extend the stubbed `elif stage == "ops"` branch, sole-writer verbatim merge, 503 fail-fast | Completes API-03 (both stages) | ✓ |
| New separate endpoint for ops | Diverges from API-03 shape | |

**Auto-selected:** Extend `/advance` ops branch, sole-writer merge (recommended default). → D-05.

---

## Escalation cards (OPS-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Typed distinct cards, conditional | Each flag = a card; clean → 0, creep+overdue → 2 | ✓ |
| Free-form flags dict | Counts not machine-checkable | |

**Auto-selected:** Typed distinct cards, conditional (recommended default). → D-06, D-07.

## Claude's Discretion

- Module layout, typed card/result model names, ops-precondition 4xx code, fixture-variant selector mechanism, deterministic creep/overdue rules, and where `build_full_supervisor` lives.

## Deferred Ideas

- Chrome extension (Phase 4); real triage tools (Phase 2); demo run/README/demo-script/diagram/license (Phase 7); AgentCore (Phase 8).
