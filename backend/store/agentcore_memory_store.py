"""AgentCoreMemoryStore: an EngagementStore backed by AgentCore Memory.

Phase 8, success criterion 1 — swapping persistence without touching agent or
API code. That works because Phase 1 put every caller behind
`EngagementStore` (D-01/D-02); this class is the second implementation of that
interface and the seam's first real test.

A NOTE ON WHAT THE ROADMAP ASKED FOR
------------------------------------
Phase 8's SC1 names `AgentCoreMemorySessionManager` as the thing to swap in.
Verified against the installed `bedrock-agentcore==1.23.0`, that class cannot
serve this role: it is a Strands `SessionManager`, and its repository
interface deals only in `Session` / `SessionAgent` / `SessionMessage` — an
agent's conversation history. It has no put/get for an arbitrary document, so
an `EngagementRecord` cannot round-trip through it. The roadmap conflated
"agent conversation memory" with "the shared Engagement Record store"; they
are different abstractions.

What AgentCore Memory does offer for document-shaped data is `BlobMessage`, an
arbitrary payload attached to a session event. So this store maps:

    one engagement            -> one AgentCore Memory session
    one save()                -> one event carrying the record as a blob
    get()                     -> the newest event's blob, re-validated

That is an append-only log with last-write-wins reads, which matches how the
record is actually used (FastAPI is the single writer, REC-03/D-05) and gives
a free audit trail of every stage transition. It is not a native document API
and is not pretending to be one.

NOT VERIFIED AGAINST A LIVE RESOURCE
------------------------------------
No AWS credentials or AgentCore Memory resource were available when this was
written, so the adapter logic is tested against an injected fake and the real
round trip has never run. The event-payload shape read back by
`_extract_record_json` follows the Bedrock API's camelCase convention and is
deliberately tolerant of several plausible shapes, but it must be confirmed
against a real resource before anyone relies on it. Strands' own docs call
this integration community-maintained and unsupported (research Pitfall 10).
The local `FileEngagementStore` remains the default and the demo path.
"""
from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from models.engagement_record import EngagementRecord
from store.engagement_store import EngagementStore

# One actor for the whole demo — the single freelancer using the system.
DEFAULT_ACTOR_ID = "freelance-autopilot"


class AgentCoreStoreError(RuntimeError):
    """A readable, diagnosable AgentCore failure.

    Carries T-01-02 forward from Phase 1: the message names the operation and
    the exception *type*, never the raw AWS message, which can echo request
    context back into logs.
    """


class AgentCoreMemoryStore(EngagementStore):
    """EngagementStore backed by one AgentCore Memory session per engagement."""

    def __init__(
        self,
        memory_id: str,
        actor_id: str = DEFAULT_ACTOR_ID,
        region_name: Optional[str] = None,
        session_manager: Any = None,
    ):
        """
        Args:
            memory_id: An existing AgentCore Memory resource id.
            actor_id: Actor the sessions belong to.
            region_name: AWS region; falls back to the boto3 chain.
            session_manager: Injected `MemorySessionManager`, for tests. When
                omitted, one is constructed and `bedrock_agentcore` is
                imported HERE rather than at module scope — so a machine
                without the optional package can still import this module,
                and more importantly the local file path (SC3) never breaks
                because of an AgentCore dependency.
        """
        self.memory_id = memory_id
        self.actor_id = actor_id

        if session_manager is not None:
            self._sessions = session_manager
            return

        try:
            from bedrock_agentcore.memory import MemorySessionManager
        except ImportError as e:
            raise AgentCoreStoreError(
                "the optional 'bedrock-agentcore' package is not installed. "
                "Install it with: pip install 'bedrock-agentcore[strands-agents]' "
                "— or unset ENGAGEMENT_STORE to use the local file store."
            ) from e

        try:
            self._sessions = MemorySessionManager(
                memory_id=memory_id, region_name=region_name
            )
        except Exception as e:  # noqa: BLE001 — type name only, never the message
            raise AgentCoreStoreError(
                f"could not open AgentCore Memory {memory_id!r} "
                f"({type(e).__name__}). Check the memory id, the region, and "
                f"that your credentials can reach AgentCore."
            ) from e

    # --- Interface ------------------------------------------------------

    def create(self, record: EngagementRecord) -> EngagementRecord:
        self.save(record)
        return record

    def save(self, record: EngagementRecord) -> None:
        """Append the whole record as a new event on the engagement's session."""
        from bedrock_agentcore.memory.constants import BlobMessage

        # Resolved BEFORE the try: a wrong-typed id is a programming error and
        # must surface as TypeError, not be laundered into AgentCoreStoreError
        # by the catch-all below.
        session_id = self._session_id(record.engagement_id)

        try:
            self._sessions.add_turns(
                actor_id=self.actor_id,
                session_id=session_id,
                messages=[BlobMessage(data=record.model_dump(mode="json"))],
            )
        except Exception as e:  # noqa: BLE001
            raise AgentCoreStoreError(
                f"could not save engagement {record.engagement_id} to "
                f"AgentCore Memory ({type(e).__name__})."
            ) from e

    def get(self, engagement_id: UUID) -> EngagementRecord | None:
        """Return the newest saved version of the record, or None."""
        session_id = self._session_id(engagement_id)  # before the try — see save()

        try:
            events = self._sessions.list_events(
                actor_id=self.actor_id,
                session_id=session_id,
                include_payload=True,
                max_results=1,
            )
        except Exception as e:  # noqa: BLE001
            # A session that has never been written to may raise rather than
            # return empty, and that is a legitimate "not found", not an
            # error the caller should have to distinguish.
            if _looks_like_not_found(e):
                return None
            raise AgentCoreStoreError(
                f"could not read engagement {engagement_id} from AgentCore "
                f"Memory ({type(e).__name__})."
            ) from e

        if not events:
            return None

        payload = _extract_record_json(events[0])
        if payload is None:
            raise AgentCoreStoreError(
                f"engagement {engagement_id}'s newest AgentCore event carried "
                f"no readable record blob."
            )
        return EngagementRecord.model_validate(payload)

    # --- Helpers --------------------------------------------------------

    @staticmethod
    def _session_id(engagement_id: UUID) -> str:
        if not isinstance(engagement_id, UUID):
            raise TypeError(
                f"AgentCoreMemoryStore requires a UUID, got "
                f"{type(engagement_id).__name__}"
            )
        return str(engagement_id)


def _looks_like_not_found(exc: Exception) -> bool:
    name = type(exc).__name__
    return "NotFound" in name or "ResourceNotFound" in name


def _extract_record_json(event: Any) -> Optional[dict]:
    """Pull the record blob out of an AgentCore event.

    Tolerant by design: `Event` is a dict wrapper over the raw Bedrock
    response, whose exact blob nesting could not be confirmed against a live
    resource. Rather than guess one shape and fail opaquely, try the
    plausible ones and let the caller raise a named error if none match.
    """
    payload = event.get("payload") if hasattr(event, "get") else None
    if payload is None:
        return None

    candidates = payload if isinstance(payload, list) else [payload]
    for item in candidates:
        blob = item.get("blob") if hasattr(item, "get") else None
        if blob is None:
            continue
        if isinstance(blob, str):
            try:
                blob = json.loads(blob)
            except json.JSONDecodeError:
                continue
        if isinstance(blob, dict):
            return blob
    return None
