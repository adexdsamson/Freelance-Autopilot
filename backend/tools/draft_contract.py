"""D-03/PROP-02/PROP-03: deterministic SOW + structured payment schedule
drafter.

Same dual-use pattern as backend/tools/placeholder_triage.py — callable
directly as a plain Python function by the deterministic ProposalRunner path
(backend/agents/proposal_runner.py) and registered as a tool on the
Proposal-Contract specialist Agent for the live path
(backend/agents/proposal_contract_agent.py).

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store imports).
"""
from __future__ import annotations

from strands import tool


@tool
def draft_contract(title: str, description: str, proposal_text: str, budget: float) -> dict:
    """Draft an SOW contract with enumerable deliverables + milestones, and a
    structured (typed) payment schedule.

    Deterministic template — no LLM call, no randomness. Returns a plain
    dict with keys "contract_text" (str) and "payment_schedule"
    (list[dict], each with label/amount/due_marker).

    `amount` is the ABSOLUTE dollar figure computed from `budget` via a
    0.3 / 0.5 / 0.2 split, rounded to 2dp (D-06/RESEARCH A2 — keep the unit
    consistent as absolute dollars, not a fraction). Only called on the
    happy path, after check_scope_clarity has confirmed budget is present —
    budget is therefore always a real number here, never None.

    WR-01: the first two milestones are independently rounded, but the
    final milestone is derived as the REMAINDER (budget - first - second)
    rather than independently rounded, so the three amounts are guaranteed
    to sum exactly to `budget` — independent per-milestone rounding can
    otherwise drift by a cent for non-round budgets (e.g. 999.99).
    """
    contract_text = (
        f"Statement of Work: {title}\n\n"
        f"Scope reference: {description.strip()}\n\n"
        f"Deliverables (per proposal):\n"
        f"  1. Discovery & scoping deliverable\n"
        f"  2. Core deliverable per agreed scope\n"
        f"  3. Final revisions & handoff package\n\n"
        f"Payment terms: milestone-based, see payment_schedule."
    )
    on_signing = round(budget * 0.3, 2)
    on_delivery = round(budget * 0.5, 2)
    final_handoff = round(budget - on_signing - on_delivery, 2)
    payment_schedule = [
        {
            "label": "On signing",
            "amount": on_signing,
            "due_marker": "on_signing",
        },
        {
            "label": "On delivery",
            "amount": on_delivery,
            "due_marker": "on_delivery",
        },
        {
            "label": "Final handoff",
            "amount": final_handoff,
            "due_marker": "net_15",
        },
    ]
    return {"contract_text": contract_text, "payment_schedule": payment_schedule}
