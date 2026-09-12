"""ORC-01/SC1/D-01: the UNIFIED three-specialist Supervisor -> name-
disambiguated Ops extraction.

All tests here are construction-only or pure-function tests -- no Bedrock
call, no AWS credentials required (matches Phase 3/5's precedent exactly).
The live four-agent Bedrock trace is documented MANUAL verification only
(D-08) -- never exercised by an automated test.
"""
import pytest
from strands import Agent

from agents.gig_triage_agent import build_gig_triage_agent
from agents.ops_agent import build_ops_agent
from agents.proposal_contract_agent import build_proposal_contract_agent
from agents.supervisor import (
    build_full_supervisor,
    build_proposal_supervisor,
    build_supervisor,
    extract_ops_result,
)
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


def test_extract_ops_result_disambiguates_by_name_among_multiple_toolresults():
    """RESEARCH.md Anti-Pattern guard (D-01): a multi-tool trace with a
    proposal_contract_agent toolResult json appearing BEFORE the ops_agent
    toolResult json must still return the OPS payload -- proving
    disambiguation by name, not a first-json-block scan."""
    proposal_payload = {
        "needs_human_input": False,
        "proposal_text": "Proposal for: Build a landing page\n...",
        "contract_text": "Statement of Work: Build a landing page\n...",
        "payment_schedule": [
            {"label": "On signing", "amount": 300.0, "due_marker": "on_signing"},
        ],
    }
    ops_payload = {
        "status_update": {"text": "1 milestone overdue."},
        "scope_creep_flags": [],
        "invoice_flags": [
            {
                "milestone_label": "On delivery",
                "due_date": "2025-01-15",
                "days_overdue": 5,
            }
        ],
    }

    messages = _tooluse_and_toolresult_messages(
        "proposal_contract_agent", proposal_payload, tool_use_id="tool-1"
    ) + _tooluse_and_toolresult_messages("ops_agent", ops_payload, tool_use_id="tool-2")

    result = extract_ops_result(messages)

    assert isinstance(result, OpsResult)
    assert result.status_update.text == "1 milestone overdue."
    assert len(result.invoice_flags) == 1
    assert result.invoice_flags[0].milestone_label == "On delivery"


def test_extract_ops_result_ignores_supervisor_prose():
    """D-02: the ops_agent toolResult json wins even when a DIFFERENT
    payload appears in the Supervisor's own assistant TEXT -- proving
    extract_ops_result never reads the Supervisor's re-authored prose."""
    payload = {
        "status_update": {"text": "1 scope item needs review."},
        "scope_creep_flags": [
            {"message": "can you also add a blog", "reason": "not in SOW"}
        ],
        "invoice_flags": [],
    }
    messages = [
        {
            "role": "assistant",
            "content": [
                {"text": "Everything looks great, no issues to report!"}
            ],
        },
        *_tooluse_and_toolresult_messages("ops_agent", payload),
    ]

    result = extract_ops_result(messages)

    assert result.status_update.text == "1 scope item needs review."
    assert len(result.scope_creep_flags) == 1


def test_extract_ops_result_tolerates_malformed_content_blocks():
    """Non-dict messages / content blocks / toolResult payloads must be
    skipped, not indexed -- no unhandled TypeError. When no valid ops_agent
    json block exists among the noise, the documented RuntimeError (never
    a raw TypeError) is raised."""
    messages = [
        "not-a-dict-message",  # non-dict message
        {"role": "assistant", "content": ["not-a-dict-block", 42]},  # non-dict blocks
        {"role": "assistant", "content": [{"toolUse": "not-a-dict"}]},  # non-dict toolUse
        {"role": "assistant", "content": [{"toolResult": "not-a-dict"}]},  # non-dict toolResult
        {
            "role": "assistant",
            "content": [{"toolResult": {"content": ["not-a-dict", 7, None]}}],  # non-dict inner blocks
        },
    ]

    with pytest.raises(RuntimeError):
        extract_ops_result(messages)


def test_full_supervisor_does_not_mutate_stage_scoped_supervisors():
    """D-01 prohibition: build_full_supervisor did NOT mutate the existing
    stage-scoped supervisors -- build_supervisor keeps exactly
    gig_triage_agent, build_proposal_supervisor keeps exactly
    proposal_contract_agent."""
    triage_supervisor = build_supervisor()
    proposal_supervisor = build_proposal_supervisor()

    assert "gig_triage_agent" in triage_supervisor.tool_names
    assert "proposal_contract_agent" not in triage_supervisor.tool_names
    assert "ops_agent" not in triage_supervisor.tool_names

    assert "proposal_contract_agent" in proposal_supervisor.tool_names
    assert "gig_triage_agent" not in proposal_supervisor.tool_names
    assert "ops_agent" not in proposal_supervisor.tool_names
