"""Shared pytest fixtures for the backend test suite."""
from pathlib import Path

import pytest

from store.file_engagement_store import FileEngagementStore


@pytest.fixture
def file_store(tmp_path: Path) -> FileEngagementStore:
    """A FileEngagementStore bound to pytest's tmp_path so tests never touch
    the real data/engagements/ directory."""
    return FileEngagementStore(base_dir=tmp_path)
