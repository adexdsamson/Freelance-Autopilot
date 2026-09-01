"""Throwaway spike: prove Strands agents-as-tools wiring + independent
tool-call traces work against the pinned strands-agents==1.54.0. NOT
imported by api.py (D-08) — this is a standalone verification spike, not
production agent code.

D-07: the specialist is wrapped in an explicit @tool-decorated function
(shape 1 of the three documented agents-as-tools shapes), not passed as a
bare Agent instance in tools=[...] — this makes the tool's name/description
explicit in code, matching the shape real Phase 2+ specialists will use.

Construction (build_supervisor) is kept separate from invocation (main) so
an offline test can assert the wiring shape without needing a Bedrock call
or AWS credentials — see tests/test_agents_as_tools_smoke.py.

NOTE on trace-inspection shape (Pitfall 1, RESEARCH.md): this sandbox has
only placeholder AWS credentials (AWS_ACCESS_KEY_ID=proxy-injected, no
AWS_REGION), so a real invoke_model call here fails fast with
botocore.exceptions.ClientError (UnrecognizedClientException) before any
tool-call trace is produced — confirmed by manually running the equivalent
of main() in this environment. The exact message/metrics shape below
(`toolUse` content blocks, `result.metrics.tool_metrics`) follows the Bedrock
Converse API's own camelCase content-block naming (which Strands preserves)
per RESEARCH.md Pattern 3 / strandsagents.com's metrics docs; it could not be
independently confirmed against a live successful call in this sandbox.
Re-verify against a real Bedrock-connected run (real creds) before relying on
this assertion in a demo.
"""
from strands import Agent, tool


@tool
def echo_specialist(message: str) -> str:
    """A throwaway specialist agent that echoes back a structured
    acknowledgment. Call this whenever the supervisor needs the echo
    specialist's response."""
    specialist = Agent(
        system_prompt="You are a specialist. Reply with exactly: SPECIALIST_ACK: <message>"
    )
    response = specialist(message)
    return str(response)


def build_supervisor() -> Agent:
    """Construct (but do not invoke) a supervisor Agent with the
    @tool-wrapped echo_specialist registered in its tools. Performs no
    network call — safe to run without AWS credentials."""
    return Agent(
        system_prompt="You route every request to the echo_specialist tool. Never answer yourself.",
        tools=[echo_specialist],
    )


def main() -> None:
    supervisor = build_supervisor()
    result = supervisor("please process: hello world")

    # Verification: prove the specialist tool was actually invoked, not just
    # answered inline by the supervisor's own model.
    tool_calls = [
        block
        for m in supervisor.messages
        if m.get("role") == "assistant"
        for block in m.get("content", [])
        if isinstance(block, dict) and "toolUse" in block
    ]
    assert tool_calls, "Supervisor never invoked a tool — check tools=[...] wiring"
    assert "echo_specialist" in str(result.metrics.tool_metrics), (
        "echo_specialist tool call not recorded in metrics"
    )
    print("PASS: agents-as-tools wiring confirmed, tool call recorded in trace")
    print(f"Final result: {result}")


if __name__ == "__main__":
    main()
