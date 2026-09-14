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


def test_capture_rejects_malformed_payload(client):
    """T-03-01: a body missing required title/description (and with no raw_text)
    fails Pydantic validation with a native 422 -- never a 500."""
    response = client.post("/capture", json={"budget": 500.0})

    assert response.status_code == 422


def test_capture_accepts_raw_text_from_extension(client):
    """Phase 4 extension contract: POST {raw_text} (what the MV3 popup sends) is
    accepted, structured fields are recovered deterministically via
    extract_job_fields (TRI-01), and triage runs to a verdict -- no Bedrock."""
    raw = (
        "Build a marketing site\n"
        "Standard React build with a clear scope and a 6-week deadline. "
        "Budget: $2,000 fixed.\n"
    )
    response = client.post("/capture", json={"raw_text": raw})

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] in ("apply", "skip")
    assert isinstance(body["score"], float)
    UUID(body["engagement_id"])

    # The extracted fields (first line -> title) reach the persisted record.
    get_body = client.get(f"/engagements/{body['engagement_id']}").json()
    assert get_body["job"]["title"] == "Build a marketing site"
    assert get_body["job"]["description"]
