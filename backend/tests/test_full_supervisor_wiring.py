"""ORC-01/SC1/D-01: the UNIFIED three-specialist Supervisor -> name-
disambiguated Ops extraction.

All tests here are construction-only or pure-function tests -- no Bedrock
call, no AWS credentials required (matches Phase 3/5's precedent exactly).
The live four-agent Bedrock trace is documented MANUAL verification only
(D-08) -- never exercised by an automated test.
"""
from strands import Agent

from agents.gig_triage_agent import build_gig_triage_agent
from agents.ops_agent import build_ops_agent
from agents.proposal_contract_agent import build_proposal_contract_agent
from agents.supervisor import build_full_supervisor, extract_ops_result
from models.engagement_record import OpsResult


def test_build_ops_agent_returns_agent():
    agent = build_ops_agent()
    assert isinstance(agent, Agent)


def test_build_ops_agent_registers_three_tools():
    agent = build_ops_agent()
    assert "check_scope_creep" in agent.tool_names
    assert "check_invoice_status" in agent.tool_names
    assert "draft_status_update" in agent.tool_names


def test_build_full_supervisor_registers_all_three_specialist_tools():
    supervisor = build_full_supervisor()
    assert isinstance(supervisor, Agent)
    assert "gig_triage_agent" in supervisor.tool_names
    assert "proposal_contract_agent" in supervisor.tool_names
    assert "ops_agent" in supervisor.tool_names


def test_four_distinct_agent_instances_exist():
    """SC1/ORC-01: build_full_supervisor() plus the three specialist
    builders must yield four DISTINCT Agent instances, not one collapsed
    call."""
    supervisor = build_full_supervisor()
    gig_triage_agent = build_gig_triage_agent()
    proposal_contract_agent = build_proposal_contract_agent()
    ops_agent = build_ops_agent()

    agents = [supervisor, gig_triage_agent, proposal_contract_agent, ops_agent]
    for agent in agents:
        assert isinstance(agent, Agent)

    for i, agent_a in enumerate(agents):
        for agent_b in agents[i + 1 :]:
            assert agent_a is not agent_b


def _tooluse_and_toolresult_messages(
    tool_name: str, json_payload: dict, tool_use_id: str = "abc123"
) -> list[dict]:
    """Builds a two-message trace: an assistant message with a toolUse
    block naming `tool_name`, followed by a toolResult message carrying
    the matching toolUseId and a json content block -- the shape
    _find_tool_result_json's two-pass algorithm requires."""
    return [
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"name": tool_name, "toolUseId": tool_use_id}}
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "status": "success",
                        "content": [{"json": json_payload}],
                    }
                }
            ],
        },
    ]


def test_extract_ops_result_reads_tool_result_block():
    payload = {
        "status_update": {"text": "Engagement is on track."},
        "scope_creep_flags": [],
        "invoice_flags": [],
    }
    messages = _tooluse_and_toolresult_messages("ops_agent", payload)

    result = extract_ops_result(messages)

    assert isinstance(result, OpsResult)
    assert result.status_update.text == "Engagement is on track."
    assert result.scope_creep_flags == []
    assert result.invoice_flags == []


def test_extract_ops_result_raises_when_absent():
    messages = [{"role": "assistant", "content": [{"text": "no tool was called"}]}]

    try:
        extract_ops_result(messages)
        assert False, "expected RuntimeError when no ops_agent toolResult json block is present"
    except RuntimeError:
        pass
