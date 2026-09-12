"""Covers ORC-03 (offline half): proves the pinned strands-agents==1.54.0
agents-as-tools API shape (Agent, tool, tools=[...]) matches assumptions,
without any network call or AWS credentials (guards Pitfall 1's
import/AttributeError risk)."""
from strands import Agent

from scripts.smoke_test_agents_as_tools import build_supervisor, echo_specialist


def test_build_supervisor_constructs_without_raising_and_returns_agent():
    supervisor = build_supervisor()
    assert isinstance(supervisor, Agent)


def test_echo_specialist_tool_is_registered_on_supervisor():
    supervisor = build_supervisor()
    assert "echo_specialist" in supervisor.tool_names
    assert echo_specialist.tool_name == "echo_specialist"
