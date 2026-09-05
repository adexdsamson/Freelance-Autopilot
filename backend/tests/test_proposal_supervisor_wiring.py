"""ORC-02 / D-01 / D-04 / D-07(f): the stage-scoped Proposal Supervisor ->
Proposal-Contract specialist typed-channel merge.

All tests here are construction-only or pure-function tests -- no Bedrock
call, no AWS credentials required (matches Phase 3's precedent exactly,
backend/tests/test_supervisor_wiring.py).
"""
from strands import Agent

from agents.proposal_contract_agent import build_proposal_contract_agent
from agents.supervisor import (
    build_proposal_supervisor,
    build_supervisor,
    extract_proposal_result,
)
from models.engagement_record import ProposalContractResult


def test_build_proposal_contract_agent_returns_agent():
    agent = build_proposal_contract_agent()
    assert isinstance(agent, Agent)


def test_build_proposal_contract_agent_registers_three_tools():
    agent = build_proposal_contract_agent()
    assert "check_scope_clarity" in agent.tool_names
    assert "draft_proposal" in agent.tool_names
    assert "draft_contract" in agent.tool_names


def test_build_proposal_supervisor_registers_proposal_contract_agent_tool():
    supervisor = build_proposal_supervisor()
    assert isinstance(supervisor, Agent)
    assert "proposal_contract_agent" in supervisor.tool_names


def test_build_supervisor_unchanged_not_extended():
    """Prohibition: build_proposal_supervisor does NOT extend build_supervisor
    -- the existing triage supervisor keeps exactly one tool, and the new
    proposal supervisor keeps exactly one (different) tool."""
    triage_supervisor = build_supervisor()
    proposal_supervisor = build_proposal_supervisor()

    assert "gig_triage_agent" in triage_supervisor.tool_names
    assert "proposal_contract_agent" not in triage_supervisor.tool_names

    assert "proposal_contract_agent" in proposal_supervisor.tool_names
    assert "gig_triage_agent" not in proposal_supervisor.tool_names


def test_two_distinct_agent_instances_exist():
    """D-04: the Proposal Supervisor and the Proposal-Contract specialist
    must be two distinct Agent instances, not one collapsed function."""
    supervisor = build_proposal_supervisor()
    proposal_contract_agent = build_proposal_contract_agent()
    assert isinstance(supervisor, Agent)
    assert isinstance(proposal_contract_agent, Agent)
    assert supervisor is not proposal_contract_agent


def _toolresult_message(json_payload: dict) -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "toolResult": {
                    "toolUseId": "abc123",
                    "status": "success",
                    "content": [{"json": json_payload}],
                }
            }
        ],
    }


def test_extract_proposal_result_reads_happy_path_tool_result_block():
    payload = {
        "needs_human_input": False,
        "proposal_text": "Proposal for: Build a landing page\n...",
        "contract_text": "Statement of Work: Build a landing page\n...",
        "payment_schedule": [
            {"label": "On signing", "amount": 300.0, "due_marker": "on_signing"},
            {"label": "On delivery", "amount": 500.0, "due_marker": "on_delivery"},
            {"label": "Final handoff", "amount": 200.0, "due_marker": "net_15"},
        ],
    }
    messages = [_toolresult_message(payload)]

    result = extract_proposal_result(messages)

    assert isinstance(result, ProposalContractResult)
    assert result.needs_human_input is False
    assert result.proposal_text == payload["proposal_text"]
    assert result.contract_text == payload["contract_text"]
    assert len(result.payment_schedule) == 3


def test_extract_proposal_result_reads_escalation_tool_result_block():
    payload = {
        "needs_human_input": True,
        "question": "Could you clarify the budget, timeline for this engagement?",
    }
    messages = [_toolresult_message(payload)]

    result = extract_proposal_result(messages)

    assert isinstance(result, ProposalContractResult)
    assert result.needs_human_input is True
    assert result.question == payload["question"]
    assert result.proposal_text is None
    assert result.contract_text is None
    assert result.payment_schedule == []


def test_extract_proposal_result_ignores_supervisor_prose():
    """D-02: the toolResult json wins even when a DIFFERENT payload appears
    in the Supervisor's own assistant TEXT -- proving extract_proposal_result
    never reads the Supervisor's re-authored prose."""
    payload = {
        "needs_human_input": True,
        "question": "Could you clarify the timeline for this engagement?",
    }
    messages = [
        {
            "role": "assistant",
            "content": [
                {"text": "Here is your proposal and contract, all set to go!"}
            ],
        },
        _toolresult_message(payload),
    ]

    result = extract_proposal_result(messages)

    assert result.needs_human_input is True
    assert result.question == payload["question"]


def test_extract_proposal_result_raises_when_absent():
    messages = [{"role": "assistant", "content": [{"text": "no tool was called"}]}]

    try:
        extract_proposal_result(messages)
        assert False, "expected RuntimeError when no toolResult json block is present"
    except RuntimeError:
        pass


def test_extract_proposal_result_tolerates_malformed_content_blocks():
    """Non-dict messages / content blocks / toolResult payloads must be
    skipped, not indexed -- no unhandled TypeError. When no valid json block
    exists among the noise, the documented RuntimeError (never a raw
    TypeError) is raised."""
    import pytest

    messages = [
        "not-a-dict-message",  # non-dict message
        {"role": "assistant", "content": ["not-a-dict-block", 42]},  # non-dict blocks
        {"role": "assistant", "content": [{"toolResult": "not-a-dict"}]},  # non-dict toolResult
        {
            "role": "assistant",
            "content": [{"toolResult": {"content": ["not-a-dict", 7, None]}}],  # non-dict inner blocks
        },
    ]

    with pytest.raises(RuntimeError):
        extract_proposal_result(messages)
