"""D-02/D-03/D-06: the OpsRunner DI seam FastAPI injects into
`/engagements/{id}/advance?stage=ops`.

Deliberately placed under backend/agents/ (not top-level) so the existing
single-writer guard (backend/tests/test_single_writer.py, which scans
backend/agents/ and backend/tools/ for store imports) covers it too — this
module must NEVER import the store (only backend/api.py may, per D-05).

Two implementations behind one `OpsRunner` Protocol, selected by the
OPS_BACKEND env var:
  - "placeholder" (default): pure-Python deterministic composition of
    check_scope_creep / check_invoice_status / draft_status_update over the
    fixture data, no Agent, no Bedrock — fully offline, used by every
    automated test (D-08).
  - "supervisor": the real unified Supervisor -> Ops specialist Agent path
    (Plan 06-02), which needs live Bedrock credentials and is a
    manual-only verification per D-08.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Protocol

from fixtures.loader import load_client_thread, load_payment_schedule
from models.engagement_record import (
    ContractSlice,
    InvoiceFlag,
    OpsResult,
    ScopeCreepFlag,
    StatusUpdate,
)
from tools.check_invoice_status import check_invoice_status
from tools.check_scope_creep import check_scope_creep
from tools.draft_status_update import draft_status_update


class OpsRunner(Protocol):
    def __call__(self, contract: ContractSlice, fixture: str) -> OpsResult: ...


def _deterministic_ops_runner(contract: ContractSlice, fixture: str) -> OpsResult:
    """D-03/D-06: calls check_scope_creep / check_invoice_status /
    draft_status_update as PLAIN Python functions (the @tool decorator
    preserves normal callability) — no Agent invocation, no Bedrock, fully
    deterministic.

    reference_date is derived from date.today() here at the call site
    (never inside check_invoice_status itself — Pitfall 1); the fixture's
    absolute ISO due dates keep the result deterministic regardless of
    when this runs.

    Always constructs OpsResult (never a bare dict — mirrors the
    proposal-runner Pitfall C convention).
    """
    thread_messages = load_client_thread(fixture)
    payment_schedule = load_payment_schedule(fixture)

    creep = check_scope_creep(contract.text or "", thread_messages)
    invoices = check_invoice_status(payment_schedule, date.today().isoformat())
    status = draft_status_update(
        creep["scope_creep_flags"], invoices["invoice_flags"]
    )

    return OpsResult(
        status_update=StatusUpdate(**status),
        scope_creep_flags=[ScopeCreepFlag(**f) for f in creep["scope_creep_flags"]],
        invoice_flags=[InvoiceFlag(**f) for f in invoices["invoice_flags"]],
    )


def _supervisor_ops_runner(contract: ContractSlice, fixture: str) -> OpsResult:
    """Live path: real unified Supervisor -> Ops specialist Agent via
    Bedrock.

    Manual-verification-only per D-08 — never exercised by an automated
    test (needs real AWS/Bedrock credentials). build_full_supervisor and
    extract_ops_result are authored in Plan 06-02; this lazy import keeps
    this module importable (and this function's Protocol conformance
    checkable) without Plan 06-02's code existing yet.
    """
    from agents.supervisor import build_full_supervisor, extract_ops_result

    supervisor = build_full_supervisor()
    supervisor(
        "Run ops checks for this signed contract and fixture data: "
        f"{contract.model_dump_json()}, fixture={fixture}"
    )
    return extract_ops_result(supervisor.messages)


def get_ops_runner() -> OpsRunner:
    """FastAPI dependency: reads OPS_BACKEND (default 'placeholder')."""
    backend = os.environ.get("OPS_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_ops_runner
    return _deterministic_ops_runner
