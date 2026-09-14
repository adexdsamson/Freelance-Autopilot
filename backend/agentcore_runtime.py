"""AgentCore Runtime entrypoint — Phase 8, success criterion 2.

Deploys the existing capture / advance flow to Bedrock AgentCore Runtime.
Run locally:

    ENGAGEMENT_STORE=agentcore AGENTCORE_MEMORY_ID=<id> python -m agentcore_runtime

This module reuses `api.py`'s handler functions rather than reimplementing
them, so the Runtime transport and the HTTP transport cannot drift: the same
triage runner, the same verbatim typed merge (ORC-02), the same store.

WHY THIS FILE MAY TOUCH THE STORE AND `agents/` MAY NOT
-------------------------------------------------------
REC-03/D-05 keeps the store behind one writer. `api.py` documents itself as
"the ONLY module in this codebase that imports the store"; this module does
not import the store directly either — it obtains one from `store.factory`
and hands it to `api.py`'s handlers, which remain the writer. It sits at
top level (not under `agents/`) so the single-writer AST guard keeps scanning
`agents/` and `tools/` unchanged.

NOT VERIFIED ON A LIVE RUNTIME. No AWS credentials or AgentCore resources were
available; the handlers below are unit-tested against a temp-dir file store,
but nothing here has been deployed to or invoked on a real AgentCore Runtime.
Treat SC2 as structurally complete and operationally unproven.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

import api
from store.engagement_store import EngagementStore
from store.factory import build_engagement_store


def handle_invocation(payload: dict, store: EngagementStore) -> dict:
    """Route one Runtime invocation to the matching api.py handler.

    Kept a plain function taking an explicit store so it is testable without
    AgentCore, a Runtime, or AWS credentials.

    Payload shapes:
        {"action": "capture", "job": {...JobSlice...}}
        {"action": "advance", "engagement_id": "...", "stage": "proposal"|"ops"}
        {"action": "get",     "engagement_id": "..."}

    Returns a JSON-safe dict, or `{"error": ...}` — a Runtime invocation
    should surface a readable failure, never a raw traceback.
    """
    action = (payload or {}).get("action")

    try:
        if action == "capture":
            # Accepts a structured job or {raw_text} (extension contract) — the
            # CaptureRequest validator resolves either into a JobSlice.
            capture_req = api.CaptureRequest.model_validate(payload.get("job") or {})
            response = api.capture(
                payload=capture_req, store=store, triage_runner=api.get_triage_runner()
            )
            return response.model_dump(mode="json")

        if action == "get":
            record = api.get_engagement(
                engagement_id=UUID(payload["engagement_id"]), store=store
            )
            return record.model_dump(mode="json")

        if action == "advance":
            record = api.advance(
                engagement_id=UUID(payload["engagement_id"]),
                body=api.AdvanceRequest(stage=payload["stage"]),
                store=store,
            )
            return record.model_dump(mode="json")

        return {
            "error": f"unknown action {action!r}. Expected: capture, advance, get."
        }
    except Exception as exc:  # noqa: BLE001 — type name only, never the message
        return {"error": f"invocation failed ({type(exc).__name__})"}


def build_app(store: Optional[EngagementStore] = None) -> Any:
    """Construct the AgentCore Runtime app.

    `bedrock_agentcore` is imported inside the function, never at module
    scope, so this module stays importable — and `handle_invocation` stays
    testable — on a machine without the optional package. That is SC3's
    guarantee: nothing about Phase 8 can break the local path.
    """
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    resolved_store = store if store is not None else build_engagement_store()
    app = BedrockAgentCoreApp()

    @app.entrypoint
    def invoke(payload: dict) -> dict:
        return handle_invocation(payload, resolved_store)

    return app


def main() -> int:
    build_app().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
