"""D-03/PROP-01: deterministic phased-scope proposal drafter.

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
def draft_proposal(title: str, description: str, budget: float) -> dict:
    """Draft a phased-scope proposal for a clear-scope apply engagement.

    Deterministic template — no LLM call, no randomness; the same input
    always produces the same output (demo-determinism). Returns a plain
    dict with key "proposal_text".

    Only called on the happy path, after check_scope_clarity has confirmed
    budget/timeline/deliverables are present — budget is therefore always
    a real number here, never None.
    """
    budget_line = f"${budget:,.2f}"
    proposal_text = (
        f"Proposal for: {title}\n\n"
        f"Summary: {description.strip()}\n\n"
        f"Approach (phased):\n"
        f"  Phase 1 — Discovery & scoping confirmation\n"
        f"  Phase 2 — Core delivery against the agreed deliverables\n"
        f"  Phase 3 — Revisions & handoff\n\n"
        f"Budget: {budget_line}"
    )
    return {"proposal_text": proposal_text}
