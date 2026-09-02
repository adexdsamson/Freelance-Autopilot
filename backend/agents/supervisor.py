"""D-01: the Supervisor Agent -- wraps the Gig Triage specialist via the
verified agents-as-tools pattern (a specialist Agent wrapped with
`.as_tool()`, passed into the Supervisor's tools=[...]).

`extract_triage_result` is the load-bearing ORC-02 mechanism: it reads the
gig_triage_agent tool's `toolResult` content block directly out of
`supervisor.messages` -- the specialist's `structured_output_model`-
validated dict, emitted by strands' `_AgentAsTool.stream()` BEFORE any
delegate/re-authoring logic runs (source-verified against the installed
strands-agents==1.54.0 package, RESEARCH.md Pattern 1). It NEVER inspects
the Supervisor's own final answer text (D-02) -- correctness here does not
depend on `delegate` firing.
"""
from __future__ import annotations

from strands import Agent

from agents.gig_triage_agent import build_gig_triage_agent
from models.engagement_record import TriageSlice


def build_supervisor() -> Agent:
    """Construct (do not invoke) the Supervisor Agent with the Gig Triage
    specialist registered as a tool. Performs no network call -- safe to
    run without AWS credentials (D-06(a)/(d))."""
    gig_triage_agent = build_gig_triage_agent()
    triage_tool = gig_triage_agent.as_tool(
        name="gig_triage_agent",
        description=(
            "Run the Gig Triage specialist (placeholder budget/keyword gate; "
            "Phase 2 will replace with extract_job_fields/kill_switch_check/"
            "llm_scorecard). Call this whenever a triage verdict is needed "
            "for a job."
        ),
        delegate=True,  # verified-compatible: BedrockModel.stateful == False
    )
    return Agent(
        system_prompt=(
            "You route every triage request to the gig_triage_agent tool. "
            "Never answer yourself."
        ),
        tools=[triage_tool],
    )


def extract_triage_result(supervisor_messages: list[dict]) -> TriageSlice:
    """Walk supervisor.messages for the first toolResult content block
    containing a "json" entry and validate it into a TriageSlice.

    Never reads the Supervisor's own final text answer (D-02) -- this is
    a structural guarantee, not a convention.
    """
    for message in supervisor_messages:
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            for content_block in block["toolResult"].get("content", []):
                if "json" in content_block:
                    return TriageSlice.model_validate(content_block["json"])
    raise RuntimeError("gig_triage_agent tool result not found in supervisor trace")
