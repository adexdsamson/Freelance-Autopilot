"""API-01: POST /capture happy path, deterministic placeholder path only
(no Bedrock — TRIAGE_BACKEND defaults to 'placeholder')."""
from uuid import UUID


def test_capture_creates_record_runs_triage_and_returns_verdict(client):
    response = client.post(
        "/capture",
        json={
            "title": "Build a landing page",
            "description": "Simple static site, no red flags",
            "budget": 500.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] in ("apply", "skip")
    assert isinstance(body["score"], float)
    assert isinstance(body["reasoning"], str) and body["reasoning"]
    # engagement_id must be a valid UUID string.
    UUID(body["engagement_id"])


def test_capture_round_trips_via_get(client):
    post_response = client.post(
        "/capture",
        json={
            "title": "Build a landing page",
            "description": "Simple static site, no red flags",
            "budget": 500.0,
        },
    )
    assert post_response.status_code == 200
    post_body = post_response.json()

    get_response = client.get(f"/engagements/{post_body['engagement_id']}")
    assert get_response.status_code == 200
    get_body = get_response.json()

    assert get_body["engagement_id"] == post_body["engagement_id"]
    assert get_body["triage"]["verdict"] == post_body["verdict"]
    assert get_body["triage"]["score"] == post_body["score"]
    assert get_body["triage"]["reasoning"] == post_body["reasoning"]
