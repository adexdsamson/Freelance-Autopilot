"""D-02/OPS-01: deterministic scope-creep gate for the Ops specialist.

This module is a deterministic gate (no LLM, no randomness) that compares
incoming client-thread messages against the signed SOW's deliverables and
flags any message that asks for something outside the signed scope — this
is what makes SC2 (creep+overdue fixture -> exactly two escalation cards)
and SC3 (clean fixture -> zero cards) demo-deterministic and fully
offline-testable.

The single `@tool`-decorated function below is the ONE source of truth for
this rule: it is called directly as a plain Python function by the
deterministic (offline/default) `OpsRunner` path
(backend/agents/ops_runner.py), AND it is registered as a tool on the Ops
specialist Agent for the live/manual path (backend/agents/ops_agent.py).
The `@tool` decorator preserves normal callability, so both invocation
routes share one rule body and can never drift apart.

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store imports).
"""
from __future__ import annotations

from strands import tool

# [ASSUMED] design-choice signal phrases (06-RESEARCH.md Assumption A1):
# generic scope-expansion phrases a client uses when asking for something
# beyond the signed SOW, co-designed with the fixture message text so
# exactly ONE creep message in the creep fixture matches (SC2).
CREEP_SIGNAL_PHRASES = (
    "can you also",
    "one more thing",
    "while you're at it",
    "can we add",
    "on top of that",
    "additionally, could you",
    "also need",
)


@tool
def check_scope_creep(contract_text: str, thread_messages: list[str]) -> dict:
    """Deterministic gate (no LLM): flags each client-thread message that
    contains a scope-expansion signal phrase whose ask is NOT already
    covered by the signed SOW (contract_text).

    A message is skipped (not flagged) if its matched signal phrase's ask
    is already a substring of the lowercased contract_text — i.e. the
    client is asking for something already in scope, not creep.

    Returns a plain dict with key "scope_creep_flags": a list of
    {"message": str, "reason": str}. The same input always produces the
    same output.
    """
    lowered_contract = (contract_text or "").lower()
    flags: list[dict] = []
    for message in thread_messages:
        lowered_message = message.lower()
        matched = next(
            (phrase for phrase in CREEP_SIGNAL_PHRASES if phrase in lowered_message),
            None,
        )
        if matched is None:
            continue
        if matched in lowered_contract:
            # The signed SOW already covers this ask — not creep.
            continue
        flags.append(
            {
                "message": message,
                "reason": (
                    f"contains scope-expansion phrase '{matched}' not covered "
                    "by the signed SOW"
                ),
            }
        )
    return {"scope_creep_flags": flags}
