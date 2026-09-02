"""D-03/D-06: the TriageRunner DI seam FastAPI injects into `/capture`.

Deliberately placed under backend/agents/ (not top-level) so the existing
single-writer guard (backend/tests/test_single_writer.py, which scans
backend/agents/ and backend/tools/ for store imports) covers it too — this
module must NEVER import the store (only backend/api.py may, per D-05).

Two implementations behind one `TriageRunner` Protocol, selected by the
TRIAGE_BACKEND env var:
  - "placeholder" (default): pure-Python deterministic rule, no Agent, no
    Bedrock — fully offline, used by every automated test (D-06(b)).
  - "supervisor": the real Supervisor -> Gig Triage specialist Agent path
    (Task 4), which needs live Bedrock credentials and is a manual-only
    verification per D-06.
"""
from __future__ import annotations

import os
from typing import Protocol

from models.engagement_record import JobSlice, TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check


class TriageRunner(Protocol):
    def __call__(self, job: JobSlice) -> TriageSlice: ...


def _deterministic_triage_runner(job: JobSlice) -> TriageSlice:
    """D-03/D-06(b): calls placeholder_kill_switch_check as a PLAIN Python
    function (the @tool decorator preserves normal callability) — no Agent
    invocation, no Bedrock, fully deterministic."""
    result = placeholder_kill_switch_check(job.budget, job.description)
    return TriageSlice.model_validate(result)


def _supervisor_triage_runner(job: JobSlice) -> TriageSlice:
    """Live path: real Supervisor -> Gig Triage Agent via Bedrock.

    TODO(Task 4): wire to backend/agents/supervisor.py's build_supervisor()
    + extract_triage_result(). Manual-verification-only per D-06 — never
    exercised by an automated test.
    """
    raise NotImplementedError("supervisor triage path is wired in Task 4")


def get_triage_runner() -> TriageRunner:
    """FastAPI dependency: reads TRIAGE_BACKEND (default 'placeholder')."""
    backend = os.environ.get("TRIAGE_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_triage_runner
    return _deterministic_triage_runner
