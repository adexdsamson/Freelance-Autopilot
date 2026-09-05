"""D-02/D-03/D-06: the ProposalRunner DI seam FastAPI injects into
`/engagements/{id}/advance?stage=proposal`.

Deliberately placed under backend/agents/ (not top-level) so the existing
single-writer guard (backend/tests/test_single_writer.py, which scans
backend/agents/ and backend/tools/ for store imports) covers it too — this
module must NEVER import the store (only backend/api.py may, per D-05).

Two implementations behind one `ProposalRunner` Protocol, selected by the
PROPOSAL_BACKEND env var:
  - "placeholder" (default): pure-Python deterministic composition of
    check_scope_clarity / draft_proposal / draft_contract, no Agent, no
    Bedrock — fully offline, used by every automated test (D-07).
  - "supervisor": the real Supervisor -> Proposal-Contract specialist Agent
    path (Plan 05-02), which needs live Bedrock credentials and is a
    manual-only verification per D-07.
"""
from __future__ import annotations

import os
from typing import Protocol

from models.engagement_record import JobSlice, ProposalContractResult
from tools.check_scope_clarity import check_scope_clarity
from tools.draft_contract import draft_contract
from tools.draft_proposal import draft_proposal


class ProposalRunner(Protocol):
    def __call__(self, job: JobSlice) -> ProposalContractResult: ...


def _deterministic_proposal_runner(job: JobSlice) -> ProposalContractResult:
    """D-03/D-07: calls check_scope_clarity / draft_proposal / draft_contract
    as PLAIN Python functions (the @tool decorator preserves normal
    callability) — no Agent invocation, no Bedrock, fully deterministic.

    Always constructs ProposalContractResult (never a bare dict — Pitfall
    C) so the D-01 mutual-exclusivity validator runs as a real assertion on
    this path too, not just on the live path.
    """
    clarity = check_scope_clarity(job.budget, job.description)
    if not clarity["clear"]:
        return ProposalContractResult(
            needs_human_input=True,
            question=clarity["question"],
        )

    proposal = draft_proposal(job.title, job.description, job.budget)
    contract = draft_contract(
        job.title, job.description, proposal["proposal_text"], job.budget
    )
    return ProposalContractResult(
        proposal_text=proposal["proposal_text"],
        contract_text=contract["contract_text"],
        payment_schedule=contract["payment_schedule"],
    )


def _supervisor_proposal_runner(job: JobSlice) -> ProposalContractResult:
    """Live path: real (stage-scoped) Supervisor -> Proposal-Contract
    specialist Agent via Bedrock.

    Manual-verification-only per D-07 — never exercised by an automated
    test (needs real AWS/Bedrock credentials). build_proposal_supervisor
    and extract_proposal_result are authored in Plan 05-02; this lazy
    import keeps this module importable (and this function's Protocol
    conformance checkable) without Plan 05-02's code existing yet.
    """
    from agents.supervisor import build_proposal_supervisor, extract_proposal_result

    supervisor = build_proposal_supervisor()
    supervisor(f"Draft a proposal and contract for this job: {job.model_dump_json()}")
    return extract_proposal_result(supervisor.messages)


def get_proposal_runner() -> ProposalRunner:
    """FastAPI dependency: reads PROPOSAL_BACKEND (default 'placeholder')."""
    backend = os.environ.get("PROPOSAL_BACKEND", "placeholder")
    if backend == "supervisor":
        return _supervisor_proposal_runner
    return _deterministic_proposal_runner
