"""D-05/SC1/SC4: POST /engagements/{id}/advance?stage=proposal, deterministic
placeholder path only (no Bedrock — PROPOSAL_BACKEND defaults to
'placeholder')."""
from uuid import uuid4

from models.engagement_record import EngagementRecord, JobSlice


def test_advance_clear_scope_returns_proposal_contract_and_round_trips(client):
    capture_response = client.post(
        "/capture",
        json={
            "title": "Build a marketing site",
            "description": (
                "Standard React build with a clear scope, three deliverable "
                "phases, and a deadline in 6 weeks."
            ),
            "budget": 2000.0,
        },
    )
    assert capture_response.status_code == 200
    engagement_id = capture_response.json()["engagement_id"]
    assert capture_response.json()["verdict"] == "apply"

    advance_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert advance_response.status_code == 200
    advance_body = advance_response.json()

    assert advance_body["proposal"]["text"]
    assert advance_body["proposal"]["needs_human_input"] is False
    assert advance_body["contract"]["text"]
    payment_schedule = advance_body["contract"]["payment_schedule"]
    assert isinstance(payment_schedule, list) and payment_schedule
    first_milestone = payment_schedule[0]
    assert set(["label", "amount", "due_marker"]).issubset(first_milestone.keys())

    get_response = client.get(f"/engagements/{engagement_id}")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["proposal"] == advance_body["proposal"]
    assert get_body["contract"] == advance_body["contract"]
    # SC4 verbatim: the persisted payment_schedule equals what advance
    # returned, not a re-authored copy.
    assert get_body["contract"]["payment_schedule"] == payment_schedule


def test_advance_unknown_engagement_returns_404(client):
    response = client.post(
        f"/engagements/{uuid4()}/advance", params={"stage": "proposal"}
    )
    assert response.status_code == 404


def test_advance_no_triage_returns_409(client, file_store):
    record = EngagementRecord(
        job=JobSlice(title="t", description="d", budget=500.0)
    )
    file_store.save(record)

    response = client.post(
        f"/engagements/{record.engagement_id}/advance", params={"stage": "proposal"}
    )
    assert response.status_code == 409


def test_advance_skip_verdict_returns_409(client):
    capture_response = client.post(
        "/capture",
        json={"title": "t", "description": "fine scope", "budget": 10.0},
    )
    assert capture_response.status_code == 200
    assert capture_response.json()["verdict"] == "skip"
    engagement_id = capture_response.json()["engagement_id"]

    response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert response.status_code == 409


def test_advance_unsupported_stage_returns_400(client):
    capture_response = client.post(
        "/capture",
        json={
            "title": "t",
            "description": (
                "Standard React build with a clear scope, three deliverable "
                "phases, and a deadline in 6 weeks."
            ),
            "budget": 2000.0,
        },
    )
    assert capture_response.status_code == 200
    assert capture_response.json()["verdict"] == "apply"
    engagement_id = capture_response.json()["engagement_id"]

    response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "ops"}
    )
    assert response.status_code == 400


def test_advance_ambiguous_scope_escalates_and_round_trips(client):
    capture_response = client.post(
        "/capture",
        json={
            "title": "t",
            "description": "Looking for someone to help with ongoing design work.",
            "budget": 500.0,
        },
    )
    assert capture_response.status_code == 200
    assert capture_response.json()["verdict"] == "apply"
    engagement_id = capture_response.json()["engagement_id"]

    advance_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert advance_response.status_code == 200
    advance_body = advance_response.json()
    assert advance_body["proposal"]["needs_human_input"] is True
    assert advance_body["proposal"]["question"]
    assert advance_body["contract"] is None

    get_response = client.get(f"/engagements/{engagement_id}")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["proposal"] == advance_body["proposal"]
    assert get_body["contract"] is None
