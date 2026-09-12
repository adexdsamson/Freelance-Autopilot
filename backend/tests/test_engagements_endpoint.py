"""API-02: GET /engagements/{id} round-trip + 404 for unknown ids."""
from uuid import uuid4


def test_get_engagement_round_trips(client):
    post_response = client.post(
        "/capture",
        json={
            "title": "Build a landing page",
            "description": "Simple static site, no red flags",
            "budget": 500.0,
        },
    )
    assert post_response.status_code == 200
    engagement_id = post_response.json()["engagement_id"]

    get_response = client.get(f"/engagements/{engagement_id}")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["engagement_id"] == engagement_id
    assert body["triage"] is not None
    assert body["triage"]["verdict"] in ("apply", "skip")


def test_get_unknown_engagement_returns_404(client):
    unknown_id = uuid4()

    response = client.get(f"/engagements/{unknown_id}")

    assert response.status_code == 404
    assert "detail" in response.json()
