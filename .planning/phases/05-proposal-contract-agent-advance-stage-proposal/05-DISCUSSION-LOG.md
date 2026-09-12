# Phase 5: Proposal-Contract Agent + `/advance` (stage="proposal") - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 5-Proposal-Contract Agent + /advance (stage="proposal")
**Mode:** `--auto` (fully autonomous discuss; recommended option auto-selected per area, no interactive prompts)
**Areas discussed:** Escalation schema shape, Deterministic vs live specialist path, Tool set & determinism, `/advance` endpoint contract, Payment-schedule representation

---

## Escalation schema shape (PROP-04, SC2/SC3)

| Option | Description | Selected |
|--------|-------------|----------|
| Single result, mutually-exclusive outcomes | One typed schema; happy path (proposal+contract+schedule) XOR escalation (needs_human_input+question) | ✓ |
| Separate proposal vs escalation responses | Two distinct response types the caller unions | |
| Optional-everywhere flat dict | Everything optional, caller infers state | |

**Auto-selected:** Single result, mutually-exclusive outcomes (recommended default).
**Notes:** `needs_human_input`/`question` first-class from the start so the ambiguous fixture escalates without a structured-output exception (STATE.md Phase-5 blocker). → D-01.

---

## Deterministic vs live specialist path

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic default + env-selected live path | Mirror Phase 3 `TriageRunner`; deterministic offline, `PROPOSAL_BACKEND` selects live | ✓ |
| Live Bedrock only | Always call the LLM specialist | |
| Deterministic only | No live path at all | |

**Auto-selected:** Deterministic default + env-selected live path (recommended default).
**Notes:** Sandbox has placeholder AWS creds; deterministic default keeps `/advance` exercisable and demo-repeatable (DEMO-02). → D-02.

---

## Tool set & determinism (PRD §7.2)

| Option | Description | Selected |
|--------|-------------|----------|
| Three §7.2 tools, dual-use, deterministic bodies | `draft_proposal`/`draft_contract`/`check_scope_clarity` as `@tool` callable both directly and via the Agent | ✓ |
| Single monolithic proposal function | One function, no tool decomposition | |
| LLM-only generation | No deterministic bodies | |

**Auto-selected:** Three §7.2 tools, dual-use, deterministic bodies (recommended default).
**Notes:** `check_scope_clarity` is a pure deterministic gate (offline-testable like `kill_switch_check`); tools must not import the store. → D-03, D-04.

---

## `/advance` endpoint contract (REC-03, SC4)

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI sole-writer, guard verdict==apply, verbatim merge, 503 fail-fast | `get`→run seam→merge proposal/contract verbatim→`save`; reuse `map_bedrock_error` | ✓ |
| Agent writes the record directly | Specialist mutates the store | |
| No guard on triage verdict | Draft regardless of verdict | |

**Auto-selected:** FastAPI sole-writer with guard + verbatim merge (recommended default).
**Notes:** Structured so Phase 6 adds `stage="ops"` without a rewrite; store already exposes `save()`. → D-05.

---

## Payment-schedule representation (PROP-03, SC1)

| Option | Description | Selected |
|--------|-------------|----------|
| Structured typed milestones | Machine-checkable, demo-deterministic | ✓ |
| Free-prose schedule inside contract text | Human-readable only | |

**Auto-selected:** Structured typed milestones (recommended default).
**Notes:** Enriching the Phase-1 `payment_schedule` stub is in scope; persisted-shape change noted as costly. → D-06.

## Claude's Discretion

- Module layout, exact typed-result model name/shape, the precise non-apply 4xx code (409 vs 422), deterministic template wording, and whether the live path extends `build_supervisor()` or uses a stage-scoped builder.

## Deferred Ideas

- Full three-agent Supervisor (ORC-01) — Phase 6.
- `stage="ops"` advancing + formal API-03 completion — Phase 6.
- Ops specialist, scope-creep/invoice tooling, Stage 2–3 fixtures (DEMO-01) — Phase 6.
- LLM-authored prose quality — live path exists behind the seam; demo runs deterministic.
