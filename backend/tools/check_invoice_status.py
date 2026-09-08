"""D-02/OPS-02: deterministic overdue-invoice gate for the Ops specialist.

This module is a deterministic gate (no LLM, no randomness) that flags
unpaid payment-schedule milestones whose due_date is before an explicit
reference_date — this is what makes SC2/SC3's escalation-card counts
demo-deterministic and fully offline-testable, PROVIDED reference_date is
always supplied explicitly by the caller (never defaulted to the wall
clock — see the module docstring's Pitfall 1 note below).

The single `@tool`-decorated function below is the ONE source of truth for
this rule: it is called directly as a plain Python function by the
deterministic (offline/default) `OpsRunner` path
(backend/agents/ops_runner.py), AND it is registered as a tool on the Ops
specialist Agent for the live/manual path (backend/agents/ops_agent.py).

Pitfall 1 (06-RESEARCH.md): reference_date is a REQUIRED "YYYY-MM-DD"
parameter with NO default. This function must NEVER call
date.today()/datetime.now() internally — doing so would make the
demo/tests time-dependent. The production call site (OpsRunner) passes
date.today().isoformat(); tests pass a fixed literal string.

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store imports).
"""
from __future__ import annotations

from datetime import date

from strands import tool


@tool
def check_invoice_status(payment_schedule: list[dict], reference_date: str) -> dict:
    """Deterministic gate (no LLM): flags each unpaid payment_schedule item
    whose due_date is strictly before reference_date.

    payment_schedule items: {"label": str, "amount": float,
    "due_date": "YYYY-MM-DD", "paid": bool}.
    reference_date: a REQUIRED "YYYY-MM-DD" ISO string — never defaulted to
    the wall clock (Pitfall 1).

    Returns a plain dict with key "invoice_flags": a list of
    {"milestone_label": str, "due_date": str, "days_overdue": int}. The
    same input always produces the same output.
    """
    today = date.fromisoformat(reference_date)
    flags: list[dict] = []
    for item in payment_schedule:
        if item.get("paid"):
            continue
        due = date.fromisoformat(item["due_date"])
        if due < today:
            flags.append(
                {
                    "milestone_label": item["label"],
                    "due_date": item["due_date"],
                    "days_overdue": (today - due).days,
                }
            )
    return {"invoice_flags": flags}
