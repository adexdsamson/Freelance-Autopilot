"""D-04: PLACEHOLDER Gig Triage specialist -- Phase 2 stand-in.

Wires a real BedrockModel + structured_output_model so the *shape* Phase 2
will fill (extract_job_fields / kill_switch_check / llm_scorecard, TRI-01..04)
is exercised end-to-end; the triage logic itself is the deterministic
placeholder_kill_switch_check tool (D-03).

Construction performs NO network call (Pitfall 2, RESEARCH.md) -- only
invoking (calling) the returned Agent touches Bedrock. This is what lets
D-06(a)/(d)'s offline construction test pass without AWS credentials.
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel

from models.engagement_record import TriageSlice
from tools.placeholder_triage import placeholder_kill_switch_check

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")


def build_gig_triage_agent() -> Agent:
    """Construct (do not invoke) the Gig Triage specialist Agent."""
    return Agent(
        name="gig_triage_agent",
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=(
            "You are the Gig Triage specialist (Phase 2 placeholder). Call "
            "placeholder_kill_switch_check with the job's budget and "
            "description, then return its result."
        ),
        tools=[placeholder_kill_switch_check],
        structured_output_model=TriageSlice,
    )
