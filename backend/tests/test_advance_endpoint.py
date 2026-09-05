"""D-05/SC1/SC4: POST /engagements/{id}/advance?stage=proposal, deterministic
placeholder path only (no Bedrock — PROPOSAL_BACKEND defaults to
'placeholder')."""


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
