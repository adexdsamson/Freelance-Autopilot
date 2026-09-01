"""Covers REC-02: FileEngagementStore create/get/save round trip, unknown-id
lookup, and atomic-write behavior (T-01-03)."""
from uuid import uuid4

from models.engagement_record import EngagementRecord, JobSlice
from store.file_engagement_store import FileEngagementStore


def test_create_then_get_round_trips_equal_record(file_store: FileEngagementStore):
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    file_store.create(record)

    reloaded = file_store.get(record.engagement_id)

    assert reloaded is not None
    assert reloaded.model_dump() == record.model_dump()


def test_get_unknown_id_returns_none(file_store: FileEngagementStore):
    assert file_store.get(uuid4()) is None


def test_save_is_atomic_no_leftover_tmp_file(file_store: FileEngagementStore, tmp_path):
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    file_store.save(record)

    json_files = list(tmp_path.glob("*.json"))
    tmp_files = list(tmp_path.glob("*.tmp"))

    assert len(json_files) == 1
    assert json_files[0] == tmp_path / f"{record.engagement_id}.json"
    assert tmp_files == []
