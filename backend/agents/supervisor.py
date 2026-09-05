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
from agents.proposal_contract_agent import build_proposal_contract_agent
from models.engagement_record import ProposalContractResult, TriageSlice


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
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            tool_result = block["toolResult"]
            if not isinstance(tool_result, dict):
                continue
            for content_block in tool_result.get("content", []):
                if isinstance(content_block, dict) and "json" in content_block:
                    return TriageSlice.model_validate(content_block["json"])
    raise RuntimeError("gig_triage_agent tool result not found in supervisor trace")


def build_proposal_supervisor() -> Agent:
    """D-04: a SEPARATE, stage-scoped Supervisor wired to only the
    Proposal-Contract specialist -- NOT an extension of build_supervisor().

    Keeping this supervisor single-tool (rather than adding a second tool to
    build_supervisor()) means extract_proposal_result's single toolResult
    scan can never accidentally pick up a different specialist's result --
    there is no toolUseId<->toolUse.name disambiguation to get wrong
    (RESEARCH.md Pattern 3). Performs no network call at construction --
    safe to run without AWS credentials (D-07(f))."""
    proposal_contract_agent = build_proposal_contract_agent()
    proposal_tool = proposal_contract_agent.as_tool(
        name="proposal_contract_agent",
        description=(
            "Draft a phased proposal + SOW contract + payment schedule for "
            "an apply engagement. Escalate with needs_human_input + a "
            "question when scope/budget is ambiguous -- never guess."
        ),
        delegate=True,  # verified-compatible: BedrockModel.stateful == False
    )
    return Agent(
        system_prompt=(
            "You route every proposal-drafting request to the "
            "proposal_contract_agent tool. Never answer yourself."
        ),
        tools=[proposal_tool],
    )


def extract_proposal_result(supervisor_messages: list[dict]) -> ProposalContractResult:
    """Walk supervisor.messages for the first toolResult content block
    containing a "json" entry and validate it into a ProposalContractResult.

    Never reads the Supervisor's own final text answer (D-02) -- this is
    a structural guarantee, not a convention.
    """
    for message in supervisor_messages:
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or "toolResult" not in block:
                continue
            tool_result = block["toolResult"]
            if not isinstance(tool_result, dict):
                continue
            for content_block in tool_result.get("content", []):
                if isinstance(content_block, dict) and "json" in content_block:
                    return ProposalContractResult.model_validate(content_block["json"])
    raise RuntimeError("proposal_contract_agent tool result not found in supervisor trace")
