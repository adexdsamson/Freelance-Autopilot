"""D-03/PROP-04: deterministic scope-clarity gate for the Proposal-Contract
specialist.

This module is a deterministic gate (no LLM, no randomness) that flags
missing budget, timeline, or deliverables signals before drafting a
proposal/contract — this is what makes SC2 (escalate on ambiguous scope
instead of guessing) demo-deterministic and fully offline-testable.

The single `@tool`-decorated function below is the ONE source of truth for
this rule: it is called directly as a plain Python function by the
deterministic (offline/default) `ProposalRunner` path
(backend/agents/proposal_runner.py), AND it is registered as a tool on the
Proposal-Contract specialist Agent for the live/manual path
(backend/agents/proposal_contract_agent.py). The `@tool` decorator preserves
normal callability, so both invocation routes share one rule body and can
never drift apart.

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store imports).
"""
from __future__ import annotations

from strands import tool

# [ASSUMED] design-choice keyword lists (05-RESEARCH.md Assumption A1): no
# structured timeline/deliverables fields exist on JobSlice, so these signals
# come from a keyword scan of the free-text description — structurally
# identical to placeholder_kill_switch_check's RED_FLAG_KEYWORDS pattern.
TIMELINE_MARKERS = {"week", "weeks", "month", "months", "deadline", "asap", "by ", "days"}
DELIVERABLE_MARKERS = {"deliverable", "milestone", "pages", "wireframe", "revisions", "phase"}


@tool
def check_scope_clarity(budget: float | None, description: str) -> dict:
    """Deterministic gate (no LLM): flags missing budget, timeline, or
    deliverables signals on a job before a proposal/contract may be drafted.

    Returns a plain dict with keys "clear" (bool) and "question"
    (str | None). The same input always produces the same output.
    """
    lowered = (description or "").lower()
    missing: list[str] = []
    if budget is None:
        missing.append("budget")
    if not any(marker in lowered for marker in TIMELINE_MARKERS):
        missing.append("timeline")
    if not any(marker in lowered for marker in DELIVERABLE_MARKERS):
        missing.append("deliverables")

    if missing:
        return {
            "clear": False,
            "question": f"Could you clarify the {', '.join(missing)} for this engagement?",
        }
    return {"clear": True, "question": None}
