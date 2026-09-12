"""D-03/D-04: Phase-2 STAND-IN for the real Gig Triage logic.

This module is a deliberately dumb, deterministic rule-of-thumb gate
(budget floor + red-flag keyword scan) so `/capture` is exercisable and
fully offline-testable before Phase 2 ships the real
`extract_job_fields` / `kill_switch_check` / `llm_scorecard` pipeline
(TRI-01..04). Phase 2 replaces the BODY of this check behind the same
`TriageRunner` seam (backend/agents/triage_runner.py) — it does not touch
any Supervisor/API code.

The single `@tool`-decorated function below is the ONE source of truth
for this rule: it is called directly as a plain Python function by the
deterministic (offline/default) `TriageRunner` path, AND it is registered
as a tool on the Gig Triage specialist Agent for the live/manual path
(backend/agents/gig_triage_agent.py). The `@tool` decorator preserves
normal callability, so both invocation routes share one rule body and can
never drift apart.

This module must NOT import the store (single-writer guard, REC-03/D-05
— backend/tests/test_single_writer.py scans backend/tools/ for store
imports).
"""
from __future__ import annotations

from strands import tool

# D-04: clearly a placeholder threshold, not a tuned business rule.
BUDGET_FLOOR = 100.0

RED_FLAG_KEYWORDS = {
    "unpaid",
    "no budget",
    "exposure",
    "equity only",
    "trial task",
    "spec work",
}


@tool
def placeholder_kill_switch_check(budget: float | None, description: str) -> dict:
    """PLACEHOLDER (Phase-2 stand-in, D-03/D-04): deterministic budget-floor +
    red-flag-keyword gate. Call this whenever a triage verdict is needed for
    a job's budget and description.

    Returns a plain dict with keys verdict ("apply"|"skip"), score (float),
    and reasoning (str) naming which rule fired. No LLM call, no randomness
    — the same input always produces the same output.
    """
    lowered_description = (description or "").lower()
    matched_keyword = next(
        (keyword for keyword in RED_FLAG_KEYWORDS if keyword in lowered_description),
        None,
    )

    if budget is not None and budget < BUDGET_FLOOR:
        return {
            "verdict": "skip",
            "score": 0.1,
            "reasoning": (
                f"budget {budget} is below the placeholder floor "
                f"({BUDGET_FLOOR}) — kill-switch rule fired."
            ),
        }

    if matched_keyword is not None:
        return {
            "verdict": "skip",
            "score": 0.1,
            "reasoning": (
                f"description contains red-flag keyword '{matched_keyword}' — "
                f"kill-switch rule fired."
            ),
        }

    return {
        "verdict": "apply",
        "score": 0.6,
        "reasoning": "no kill-switch rule fired (budget floor and keyword scan both passed).",
    }
