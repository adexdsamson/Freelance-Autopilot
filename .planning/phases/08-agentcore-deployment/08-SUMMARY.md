# Phase 8 Summary: AgentCore Deployment (optional, cut-first)

**Completed:** 2026-09-11
**Branch:** `gsd/phase-08-agentcore-deployment` (cut from Phase 7's head)
**Requirements:** none in v1 by design; addresses v2 DEPLOY-01, DEPLOY-02

## What Was Built

| File | Purpose |
|---|---|
| `backend/store/agentcore_memory_store.py` | `EngagementStore` backed by AgentCore Memory |
| `backend/store/factory.py` | The single construction point; `ENGAGEMENT_STORE` selects the backend |
| `backend/agentcore_runtime.py` | Runtime entrypoint routing to `api.py`'s handlers |
| `backend/tests/test_store_factory.py` | 12 tests — SC1 selection + SC3 protection |
| `backend/tests/test_agentcore_memory_store.py` | 16 tests — adapter contract and failure modes |
| `backend/tests/test_agentcore_runtime.py` | 11 tests — routing, handler reuse, no leakage |

Full suite: **164 passed** (125 inherited from Phase 7, 39 new).

## Success Criteria

| # | Criterion | Status |
|---|---|---|
| 1 | Store swappable to AgentCore behind the interface, no agent/API change | **Met, with a correction** — see below |
| 2 | Supervisor + specialists on Runtime process capture-through-advance | **Structurally complete, operationally unproven** |
| 3 | Local file path still works end to end if this phase is abandoned | **Met and enforced by test** |

### SC1 — the roadmap named the wrong class

SC1 says to swap the store to `AgentCoreMemorySessionManager`. Verified against
the installed `bedrock-agentcore==1.23.0`, that is not possible:
`AgentCoreMemorySessionManager` is a Strands `SessionManager`, and its
repository interface (`create_session`, `create_message`, `read_agent`, …)
deals only in `Session` / `SessionAgent` / `SessionMessage` — an agent's
conversation history. There is no put/get for an arbitrary document, so an
`EngagementRecord` cannot round-trip through it. The roadmap conflated *agent
conversation memory* with *the shared Engagement Record store*.

What AgentCore Memory does offer for document-shaped data is `BlobMessage`, so
the adapter maps one engagement to one Memory session and one `save()` to one
event carrying the record as a blob. Reads take the newest event. That is
append-only with last-write-wins, which suits a single-writer record (REC-03)
and yields a free audit trail of every stage transition.

The *intent* of SC1 — persistence swappable behind the interface with no agent
or API change — is met: `api.py`'s `get_store()` now asks the factory, and that
one line was the entire edit.

### SC2 — built but never deployed

The entrypoint reuses `api.py`'s handlers rather than reimplementing them, so
the Runtime and HTTP transports cannot drift. It has never been deployed to or
invoked on a real AgentCore Runtime, because no AWS credentials were available.

### SC3 — enforced, not asserted

The local path is the default and cannot be broken by this phase:

- Neither `store/factory.py` nor `agentcore_runtime.py` imports
  `bedrock_agentcore` at module scope — checked by AST, not by convention.
- A subprocess test blocks `bedrock_agentcore` at import time in a fresh
  interpreter and still imports `api.py` and `agentcore_runtime`, then
  round-trips a record through the file store.
- `bedrock-agentcore` is an optional extra in `pyproject.toml`, never a
  dependency.

Reverting this phase is `git revert` plus dropping the extra. Nothing else
depends on it.

## Not Verified

No AWS credentials or AgentCore resources were available, so **nothing in this
phase has touched real AgentCore.** Specifically unproven:

1. That a real `MemorySessionManager` accepts the `add_turns` / `list_events`
   calls as shaped here.
2. The event payload nesting. `_extract_record_json` accepts several plausible
   shapes rather than guessing one, but the real one is unconfirmed.
3. That `list_events` returns newest-first, which `get()` assumes.
4. Any Runtime deployment or invocation.

Before relying on this: create a Memory resource, then
`ENGAGEMENT_STORE=agentcore AGENTCORE_MEMORY_ID=<id> python -m scripts.run_demo`
and confirm the record round-trips.

## One bug found by testing

`get()` and `save()` resolved the session id *inside* the try block, so a
wrong-typed `engagement_id` — a programming error — was being laundered into
`AgentCoreStoreError` by the catch-all, hiding the bug. The guard now runs
before the try, matching `FileEngagementStore`.
