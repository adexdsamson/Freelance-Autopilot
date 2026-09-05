"""Covers REC-01: EngagementRecord validates job-only, rejects invalid triage verdict,
and closes off path-traversal via UUID-typed engagement_id (T-01-01)."""
import pytest
from pydantic import ValidationError

from models.engagement_record import EngagementRecord, JobSlice, TriageSlice


def test_job_only_record_validates_with_uuid_engagement_id():
    record = EngagementRecord(job=JobSlice(title="t", description="d"))
    assert record.triage is None
    assert record.proposal is None
    assert record.contract is None
    assert record.ops is None
    # engagement_id auto-assigned as a UUID (default_factory=uuid4, D-04)
    assert str(record.engagement_id)  # renders without error
    assert record.engagement_id.version == 4


def test_invalid_triage_verdict_raises_validation_error():
    with pytest.raises(ValidationError):
        TriageSlice(verdict="maybe", score=1, reasoning="x")


def test_path_traversal_engagement_id_raises_validation_error():
    with pytest.raises(ValidationError):
        EngagementRecord(
            engagement_id="../../etc/passwd",
            job=JobSlice(title="t", description="d"),
        )
