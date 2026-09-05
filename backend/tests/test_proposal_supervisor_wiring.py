"""ORC-02 / D-01 / D-04 / D-07(f): the stage-scoped Proposal Supervisor ->
Proposal-Contract specialist typed-channel merge.

All tests here are construction-only or pure-function tests -- no Bedrock
call, no AWS credentials required (matches Phase 3's precedent exactly,
backend/tests/test_supervisor_wiring.py).
"""
from strands import Agent

from agents.proposal_contract_agent import build_proposal_contract_agent


def test_build_proposal_contract_agent_returns_agent():
    agent = build_proposal_contract_agent()
    assert isinstance(agent, Agent)


def test_build_proposal_contract_agent_registers_three_tools():
    agent = build_proposal_contract_agent()
    assert "check_scope_clarity" in agent.tool_names
    assert "draft_proposal" in agent.tool_names
    assert "draft_contract" in agent.tool_names
