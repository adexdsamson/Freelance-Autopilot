"""Covers the AgentCoreMemoryStore adapter (Phase 8, SC1).

Every test drives an INJECTED fake session manager. No AWS credentials and no
AgentCore Memory resource were available, so what is proven here is the
adapter's own logic — the interface contract, the session-per-engagement
mapping, blob round-tripping, and readable failures. The live round trip is
explicitly NOT proven; see the module docstring on
`store/agentcore_memory_store.py`.
"""
import pytest

# The AgentCore adapter is the cut-first Phase 8 stretch: the `bedrock-agentcore`
# package is an optional extra (see pyproject `[project.optional-dependencies]
# agentcore`), so the default offline suite runs without it installed. Skip this
# module's adapter tests when the package is absent rather than breaking
# collection of the whole suite — matching how the store module itself lazily
# imports the dependency so the file-store path never requires it.
pytest.importorskip("bedrock_agentcore")

from bedrock_agentcore.memory.constants import BlobMessage
from models.engagement_record import EngagementRecord, JobSlice, TriageSlice
from store.agentcore_memory_store import (
    AgentCoreMemoryStore,
    AgentCoreStoreError,
    _extract_record_json,
)
from store.engagement_store import EngagementStore


class FakeSessions:
    """Stands in for MemorySessionManager, matching the real signatures.

    Events are appended and returned newest-first, mirroring what the adapter
    assumes when it asks for max_results=1.
    """

    def __init__(self):
        self.events: dict[str, list] = {}
        self.calls: list[tuple] = []

    def add_turns(self, actor_id, session_id, messages, **kwargs):
        self.calls.append(("add_turns", actor_id, session_id))
        payload = [{"blob": m.data} for m in messages]
        self.events.setdefault(session_id, []).insert(0, {"payload": payload})

    def list_events(self, actor_id, session_id, include_payload=True, max_results=100, **kw):
        self.calls.append(("list_events", actor_id, session_id))
        return self.events.get(session_id, [])[:max_results]


@pytest.fixture
def sessions():
    return FakeSessions()


@pytest.fixture
def store(sessions):
    return AgentCoreMemoryStore(memory_id="mem-test", session_manager=sessions)


@pytest.fixture
def record():
    return EngagementRecord(
        job=JobSlice(title="Rebuild dashboard", description="React work", budget=8500.0),
        triage=TriageSlice(verdict="apply", score=72.5, reasoning="Clear scope."),
    )


def test_it_is_an_engagement_store(store):
    assert isinstance(store, EngagementStore)


def test_save_then_get_round_trips_the_whole_record(store, record):
    store.save(record)
    assert store.get(record.engagement_id) == record


def test_create_persists_and_returns_the_record(store, record):
    assert store.create(record) is record
    assert store.get(record.engagement_id) == record


def test_get_returns_none_for_an_engagement_never_saved(store, record):
    assert store.get(record.engagement_id) is None


def test_each_engagement_maps_to_its_own_session(store, sessions, record):
    store.save(record)
    other = EngagementRecord(job=JobSlice(title="Other", description="d"))
    store.save(other)
    assert set(sessions.events) == {str(record.engagement_id), str(other.engagement_id)}


def test_save_appends_rather_than_overwriting_so_history_survives(store, sessions, record):
    """Append-only is the point: every stage transition stays auditable."""
    store.save(record)
    record.triage = TriageSlice(verdict="skip", score=10.0, reasoning="Changed.")
    store.save(record)
    assert len(sessions.events[str(record.engagement_id)]) == 2


def test_get_returns_the_newest_version(store, record):
    store.save(record)
    record.triage = TriageSlice(verdict="skip", score=10.0, reasoning="Changed.")
    store.save(record)
    reloaded = store.get(record.engagement_id)
    assert reloaded.triage.verdict == "skip"
    assert reloaded.triage.score == 10.0


def test_a_non_uuid_engagement_id_is_rejected(store):
    """Mirrors FileEngagementStore's guard — a raw string must never become a
    session id."""
    with pytest.raises(TypeError):
        store.get("../../etc/passwd")


def test_a_backend_failure_becomes_a_named_error_not_a_raw_traceback(record):
    class Exploding:
        def add_turns(self, **kwargs):
            raise RuntimeError("boom AKIA-secret-in-message")

    store = AgentCoreMemoryStore(memory_id="m", session_manager=Exploding())
    with pytest.raises(AgentCoreStoreError) as excinfo:
        store.save(record)
    message = str(excinfo.value)
    assert "RuntimeError" in message
    assert "AKIA-secret-in-message" not in message  # T-01-02 carried forward


def test_a_not_found_style_error_reads_as_absent_not_as_a_failure(record):
    class NotThere:
        def list_events(self, **kwargs):
            raise type("ResourceNotFoundException", (Exception,), {})()

    store = AgentCoreMemoryStore(memory_id="m", session_manager=NotThere())
    assert store.get(record.engagement_id) is None


def test_an_event_with_no_readable_blob_is_a_named_error(record):
    class Empty:
        def list_events(self, **kwargs):
            return [{"payload": [{"conversational": {"text": "not a record"}}]}]

    store = AgentCoreMemoryStore(memory_id="m", session_manager=Empty())
    with pytest.raises(AgentCoreStoreError, match="no readable record blob"):
        store.get(record.engagement_id)


@pytest.mark.parametrize(
    "event",
    [
        {"payload": [{"blob": {"a": 1}}]},          # blob as an object
        {"payload": [{"blob": '{"a": 1}'}]},        # blob as a JSON string
        {"payload": {"blob": {"a": 1}}},            # payload not a list
    ],
)
def test_blob_extraction_tolerates_the_plausible_payload_shapes(event):
    """The live payload nesting could not be confirmed without a real
    resource, so the reader accepts each shape rather than guessing one and
    failing opaquely."""
    assert _extract_record_json(event) == {"a": 1}


def test_blob_extraction_returns_none_when_there_is_nothing_to_read():
    assert _extract_record_json({}) is None
    assert _extract_record_json({"payload": []}) is None


def test_blob_message_is_the_real_sdk_type(store, sessions, record):
    """Guards against the adapter drifting from bedrock-agentcore's API: the
    message handed to add_turns must be a genuine BlobMessage."""
    captured = []

    def capture(actor_id, session_id, messages, **kwargs):
        captured.extend(messages)

    sessions.add_turns = capture
    store.save(record)
    assert isinstance(captured[0], BlobMessage)
