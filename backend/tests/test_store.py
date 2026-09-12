"""Covers REC-02: FileEngagementStore create/get/save round trip, unknown-id
lookup, update-in-place of an already-persisted record, corrupt-file
diagnosis, and atomic-write behavior (T-01-03)."""
from uuid import uuid4

import pytest

from models.engagement_record import EngagementRecord, JobSlice
from store.file_engagement_store import FileEngagementStore, StoreCorruptError


def test_create_then_get_round_trips_equal_record(file_store: FileEngagementStore):
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    file_store.create(record)

    reloaded = file_store.get(record.engagement_id)

    assert reloaded is not None
    assert reloaded.model_dump() == record.model_dump()


def test_get_unknown_id_returns_none(file_store: FileEngagementStore):
    assert file_store.get(uuid4()) is None


def test_save_updates_already_persisted_record(file_store: FileEngagementStore):
    record = EngagementRecord(job=JobSlice(title="original", description="d"))
    file_store.create(record)

    # Re-save under the SAME engagement_id with a changed field.
    updated = EngagementRecord(
        engagement_id=record.engagement_id,
        job=JobSlice(title="updated", description="d"),
    )
    file_store.save(updated)

    reloaded = file_store.get(record.engagement_id)
    assert reloaded is not None
    assert reloaded.job.title == "updated"


def test_get_corrupt_file_raises_store_corrupt_error(
    file_store: FileEngagementStore, tmp_path
):
    bad_id = uuid4()
    (tmp_path / f"{bad_id}.json").write_text("{ this is not valid json")

    with pytest.raises(StoreCorruptError) as exc:
        file_store.get(bad_id)

    # Diagnostic names the id; never echoes the raw (possibly sensitive) content.
    assert str(bad_id) in str(exc.value)
    assert "this is not valid json" not in str(exc.value)


def test_save_is_atomic_no_leftover_tmp_file(file_store: FileEngagementStore, tmp_path):
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    file_store.save(record)

    json_files = list(tmp_path.glob("*.json"))
    tmp_files = list(tmp_path.glob("*.tmp"))

    assert len(json_files) == 1
    assert json_files[0] == tmp_path / f"{record.engagement_id}.json"
    assert tmp_files == []
