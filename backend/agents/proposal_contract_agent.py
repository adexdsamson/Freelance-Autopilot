"""D-04: the Proposal-Contract specialist -- Phase 5's second genuine agent.

Wires a real BedrockModel + structured_output_model=ProposalContractResult so
this specialist's typed result (PROP-01..04: check_scope_clarity gate, then
draft_proposal + draft_contract) is produced on the live path exactly as it
is on the deterministic path (backend/agents/proposal_runner.py's
_deterministic_proposal_runner) -- both call the SAME three @tool functions,
so the two paths can never drift apart.

Construction performs NO network call (mirrors gig_triage_agent.py) -- only
invoking (calling) the returned Agent touches Bedrock. This is what lets
D-07(f)'s offline construction test pass without AWS credentials.

This module must NOT import the store (single-writer guard, REC-03/D-05 --
backend/tests/test_single_writer.py scans backend/agents/ for store imports).
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import ProposalContractResult
from tools.check_scope_clarity import check_scope_clarity
from tools.draft_contract import draft_contract
from tools.draft_proposal import draft_proposal

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_proposal_contract_agent() -> Agent:
    """Construct (do not invoke) the Proposal-Contract specialist Agent."""
    return Agent(
        name="proposal_contract_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Proposal-Contract specialist. Always call "
            "check_scope_clarity first with the job's budget and "
            "description. If it reports the scope is not clear, do NOT "
            "guess -- return needs_human_input=True with its question "
            "verbatim. Only when the scope is clear should you call "
            "draft_proposal, then draft_contract with the drafted "
            "proposal text, and return the resulting proposal_text, "
            "contract_text, and payment_schedule."
        ),
        tools=[check_scope_clarity, draft_proposal, draft_contract],
        structured_output_model=ProposalContractResult,
    )
