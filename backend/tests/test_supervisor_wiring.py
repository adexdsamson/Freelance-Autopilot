"""ORC-02 / D-01 / D-06(a)(d): the Supervisor -> Gig Triage specialist
typed-channel merge.

All tests here are construction-only or pure-function tests -- no Bedrock
call, no AWS credentials required (matches Phase 1's precedent exactly).
"""
from strands import Agent

from agents.gig_triage_agent import build_gig_triage_agent
from agents.supervisor import build_supervisor, extract_triage_result
from models.engagement_record import TriageSlice


def test_build_supervisor_registers_gig_triage_agent_tool():
    supervisor = build_supervisor()
    assert isinstance(supervisor, Agent)
    assert "gig_triage_agent" in supervisor.tool_names


def test_two_distinct_agent_instances_exist():
    """D-01/D-06(a)(d): the Supervisor and the Gig Triage specialist must be
    two distinct Agent instances, not one collapsed function."""
    supervisor = build_supervisor()
    gig_triage_agent = build_gig_triage_agent()
    assert isinstance(supervisor, Agent)
    assert isinstance(gig_triage_agent, Agent)
    assert supervisor is not gig_triage_agent


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


def test_extract_triage_result_reads_tool_result_block():
    payload = {"verdict": "apply", "score": 0.8, "reasoning": "looks solid"}
    messages = [_toolresult_message(payload)]

    result = extract_triage_result(messages)

    assert isinstance(result, TriageSlice)
    assert result.verdict == "apply"
    assert result.score == 0.8
    assert result.reasoning == "looks solid"


def test_extract_triage_result_ignores_supervisor_prose():
    """D-02: the toolResult json wins even when a DIFFERENT verdict appears
    in the Supervisor's own assistant TEXT -- proving extract_triage_result
    never reads the Supervisor's re-authored prose."""
    payload = {"verdict": "skip", "score": 0.1, "reasoning": "budget too low"}
    messages = [
        {
            "role": "assistant",
            "content": [{"text": "Verdict: apply -- this looks like a great gig!"}],
        },
        _toolresult_message(payload),
    ]

    result = extract_triage_result(messages)

    assert result.verdict == "skip"
    assert result.reasoning == "budget too low"


def test_extract_triage_result_raises_when_absent():
    messages = [{"role": "assistant", "content": [{"text": "no tool was called"}]}]

    try:
        extract_triage_result(messages)
        assert False, "expected RuntimeError when no toolResult json block is present"
    except RuntimeError:
        pass
