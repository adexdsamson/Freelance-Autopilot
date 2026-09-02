"""T-03-02 / D-06: /capture must fail fast + readably (503, not a raw 500
traceback) when the (mocked) live Bedrock path raises. No live Bedrock call
is made here -- a triage_runner override raises the exception type
directly."""
import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from strands.types.exceptions import (
    ContextWindowOverflowException,
    ModelThrottledException,
)

from api import app, get_triage_runner


def _raising_runner(exc: Exception):
    def _runner(job):
        raise exc

    return _runner


@pytest.mark.parametrize(
    "exc",
    [
        ModelThrottledException("throttled"),  # strands, NOT a BotoCoreError (CR-01)
        ContextWindowOverflowException("overflow"),  # strands (CR-01)
        RuntimeError("some entirely unexpected triage failure"),  # catch-all (CR-01)
    ],
)
def test_capture_maps_non_botocore_triage_failures_to_503_not_500(client, exc):
    """CR-01 regression: a live-path triage failure that is NOT a botocore
    exception (strands throttle/context-overflow, or any unexpected type) must
    still become a readable 503 — never a raw 500 traceback, never a leak."""
    app.dependency_overrides[get_triage_runner] = lambda: _raising_runner(exc)
    try:
        response = client.post(
            "/capture",
            json={"title": "t", "description": "d", "budget": 500.0},
        )
    finally:
        del app.dependency_overrides[get_triage_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "proxy-injected" not in detail
    assert isinstance(detail, str) and detail


def test_capture_returns_503_on_bedrock_client_error(client):
    error_response = {"Error": {"Code": "AccessDeniedException", "Message": "top secret detail"}}
    app.dependency_overrides[get_triage_runner] = lambda: _raising_runner(
        ClientError(error_response, "InvokeModel")
    )
    try:
        response = client.post(
            "/capture",
            json={"title": "t", "description": "d", "budget": 500.0},
        )
    finally:
        del app.dependency_overrides[get_triage_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "top secret detail" not in detail
    assert "proxy-injected" not in detail
    assert "AccessDeniedException" in detail


def test_capture_maps_no_credentials(client):
    app.dependency_overrides[get_triage_runner] = lambda: _raising_runner(NoCredentialsError())
    try:
        response = client.post(
            "/capture",
            json={"title": "t", "description": "d", "budget": 500.0},
        )
    finally:
        del app.dependency_overrides[get_triage_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "proxy-injected" not in detail
    assert "credentials" in detail.lower()
