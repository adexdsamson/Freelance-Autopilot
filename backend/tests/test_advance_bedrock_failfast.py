"""D-07(g): /advance must fail fast + readably (503, not a raw 500
traceback) when the (mocked) live Bedrock path raises. No live Bedrock call
is made here -- a proposal_runner override raises the exception type
directly. Mirrors test_capture_bedrock_failfast.py exactly."""
import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from strands.types.exceptions import (
    ContextWindowOverflowException,
    ModelThrottledException,
)

from api import app, get_proposal_runner


def _raising_runner(exc: Exception):
    def _runner(job):
        raise exc

    return _runner


def _capture_apply_engagement(client):
    capture_response = client.post(
        "/capture",
        json={
            "title": "t",
            "description": (
                "Standard React build with a clear scope, three deliverable "
                "phases, and a deadline in 6 weeks."
            ),
            "budget": 500.0,
        },
    )
    assert capture_response.status_code == 200
    assert capture_response.json()["verdict"] == "apply"
    return capture_response.json()["engagement_id"]


@pytest.mark.parametrize(
    "exc",
    [
        ModelThrottledException("throttled"),  # strands, NOT a BotoCoreError (CR-01)
        ContextWindowOverflowException("overflow"),  # strands (CR-01)
        RuntimeError("some entirely unexpected proposal-drafting failure"),  # catch-all
    ],
)
def test_advance_maps_non_botocore_failures_to_503_not_500(client, exc):
    """CR-01-style regression: a live-path failure that is NOT a botocore
    exception (strands throttle/context-overflow, or any unexpected type)
    must still become a readable 503 — never a raw 500 traceback, never a leak."""
    engagement_id = _capture_apply_engagement(client)

    app.dependency_overrides[get_proposal_runner] = lambda: _raising_runner(exc)
    try:
        response = client.post(
            f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
        )
    finally:
        del app.dependency_overrides[get_proposal_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "proxy-injected" not in detail
    assert isinstance(detail, str) and detail


def test_advance_returns_503_on_bedrock_client_error(client):
    engagement_id = _capture_apply_engagement(client)

    error_response = {"Error": {"Code": "AccessDeniedException", "Message": "top secret detail"}}
    app.dependency_overrides[get_proposal_runner] = lambda: _raising_runner(
        ClientError(error_response, "InvokeModel")
    )
    try:
        response = client.post(
            f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
        )
    finally:
        del app.dependency_overrides[get_proposal_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "top secret detail" not in detail
    assert "proxy-injected" not in detail
    assert "AccessDeniedException" in detail


def test_advance_maps_no_credentials(client):
    engagement_id = _capture_apply_engagement(client)

    app.dependency_overrides[get_proposal_runner] = lambda: _raising_runner(
        NoCredentialsError()
    )
    try:
        response = client.post(
            f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
        )
    finally:
        del app.dependency_overrides[get_proposal_runner]

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "proxy-injected" not in detail
    assert "credentials" in detail.lower()
