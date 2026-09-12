"""Shared pytest fixtures for the backend test suite."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from store.file_engagement_store import FileEngagementStore


@pytest.fixture
def file_store(tmp_path: Path) -> FileEngagementStore:
    """A FileEngagementStore bound to pytest's tmp_path so tests never touch
    the real data/engagements/ directory."""
    return FileEngagementStore(base_dir=tmp_path)


@pytest.fixture
def client(file_store: FileEngagementStore):
    """A TestClient for backend.api's FastAPI app, with the store dependency
    overridden to the tmp-path-bound `file_store` fixture so tests never
    touch the real data/engagements/ directory. Overrides are cleared on
    teardown so tests don't leak state into each other."""
    from api import app, get_store

    app.dependency_overrides[get_store] = lambda: file_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
