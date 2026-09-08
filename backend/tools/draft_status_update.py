"""D-02/OPS-03/SC4: deterministic client-ready status-update drafter.

Same dual-use pattern as backend/tools/draft_proposal.py — callable
directly as a plain Python function by the deterministic OpsRunner path
(backend/agents/ops_runner.py) and registered as a tool on the Ops
specialist Agent for the live path (backend/agents/ops_agent.py).

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store imports).
"""
from __future__ import annotations

from strands import tool


@tool
def draft_status_update(scope_creep_flags: list[dict], invoice_flags: list[dict]) -> dict:
    """Draft a client-ready status update reflecting whichever flags are
    currently active (OPS-03/SC4).

    Deterministic template — no LLM call, no randomness; the same input
    always produces the same output (demo-determinism). Returns a plain
    dict with key "text".
    """
    lines = ["Status update:"]
    if not scope_creep_flags and not invoice_flags:
        lines.append(
            "Engagement is on track — no scope or invoicing concerns to flag."
        )
    if scope_creep_flags:
        lines.append(
            f"{len(scope_creep_flags)} scope item(s) outside the signed SOW "
            "were raised in the client thread and need review before "
            "proceeding."
        )
    if invoice_flags:
        lines.append(
            f"{len(invoice_flags)} milestone(s) are overdue against the "
            "payment schedule and need follow-up."
        )
    return {"text": "\n".join(lines)}
