"""D-02: the Ops specialist -- Phase 6's third genuine agent.

Wires a real BedrockModel + structured_output_model=OpsResult so this
specialist's typed result (OPS-01..03: check_scope_creep +
check_invoice_status, then draft_status_update reflecting whichever flags
are active) is produced on the live path exactly as it is on the
deterministic path (backend/agents/ops_runner.py's
_deterministic_ops_runner) -- both call the SAME three @tool functions, so
the two paths can never drift apart.

Construction performs NO network call (mirrors gig_triage_agent.py /
proposal_contract_agent.py) -- only invoking (calling) the returned Agent
touches Bedrock. This is what lets the offline construction test pass
without AWS credentials.

Pitfall 4 (06-RESEARCH.md): structured_output_model=OpsResult is REQUIRED --
without it, the live toolResult path falls through to the `delegate`
branch (raw text/json from the specialist's own final message) instead of
the guaranteed `result.structured_output` channel.

This module must NOT import the store (single-writer guard, REC-03 --
backend/tests/test_single_writer.py scans backend/agents/ for store
imports).
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import OpsResult
from tools.check_invoice_status import check_invoice_status
from tools.check_scope_creep import check_scope_creep
from tools.draft_status_update import draft_status_update

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_ops_agent() -> Agent:
    """Construct (do not invoke) the Ops specialist Agent."""
    return Agent(
        name="ops_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Ops specialist. Always call check_scope_creep and "
            "check_invoice_status to gather the current scope-creep and "
            "overdue-invoice flags, then call draft_status_update with "
            "those flags to produce a client-ready status update. Return "
            "the resulting status_update, scope_creep_flags, and "
            "invoice_flags."
        ),
        tools=[check_scope_creep, check_invoice_status, draft_status_update],
        structured_output_model=OpsResult,
    )
