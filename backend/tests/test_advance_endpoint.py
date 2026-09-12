"""D-05/SC1/SC4: POST /engagements/{id}/advance?stage=proposal, deterministic
placeholder path only (no Bedrock — PROPOSAL_BACKEND defaults to
'placeholder')."""
from uuid import uuid4

from api import app, get_proposal_runner
from models.engagement_record import EngagementRecord, JobSlice, ProposalContractResult


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
        f"/engagements/{engagement_id}/advance", params={"stage": "review"}
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


def test_advance_ops_after_proposal_completes_both_stages(client):
    """API-03/SC5/D-05: one engagement advances through stage=proposal then
    stage=ops, each call returning the updated record. SC2/D-06: the
    creep+overdue fixture yields exactly 2 escalation cards through the ops
    branch."""
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

    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert proposal_response.status_code == 200
    assert proposal_response.json()["contract"]["text"]

    ops_response = client.post(
        f"/engagements/{engagement_id}/advance",
        params={"stage": "ops", "fixture": "creep"},
    )
    assert ops_response.status_code == 200
    ops_body = ops_response.json()
    assert (
        len(ops_body["ops"]["scope_creep_flags"])
        + len(ops_body["ops"]["invoice_flags"])
        == 2
    )
    assert ops_body["ops"]["status_updates"]

    get_response = client.get(f"/engagements/{engagement_id}")
    assert get_response.status_code == 200
    assert get_response.json()["ops"] == ops_body["ops"]


def test_advance_ops_without_contract_returns_409(client):
    """Pitfall 3/T-06-PT: a headless engagement (capture only, never
    advanced through stage=proposal) must not be advanceable to ops."""
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

    response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "ops"}
    )
    assert response.status_code == 409


def test_advance_ops_when_proposal_escalated_returns_409(client):
    """Pitfall 3/T-06-PT: an escalated proposal (needs_human_input=True, no
    contract) must not be advanceable to ops."""
    capture_response = client.post(
        "/capture",
        json={
            "title": "t",
            "description": "Looking for someone to help with ongoing design work.",
            "budget": 500.0,
        },
    )
    assert capture_response.status_code == 200
    engagement_id = capture_response.json()["engagement_id"]

    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert proposal_response.status_code == 200
    assert proposal_response.json()["proposal"]["needs_human_input"] is True
    assert proposal_response.json()["contract"] is None

    response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "ops"}
    )
    assert response.status_code == 409


def test_advance_ops_out_of_set_fixture_returns_422(client):
    """T-06-PT: the fixture query param is a closed Literal["creep","clean"]
    set — an out-of-range value (e.g. a path-traversal attempt) is
    structurally rejected with a 422, never interpolated into a path."""
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

    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert proposal_response.status_code == 200

    response = client.post(
        f"/engagements/{engagement_id}/advance",
        params={"stage": "ops", "fixture": "../../etc/passwd"},
    )
    assert response.status_code == 422


def test_advance_re_advance_escalation_clears_stale_contract(client):
    """CR-01 regression: re-advancing the same engagement, happy path then
    escalation, must clear the previously-persisted contract at BOTH the
    HTTP response and the persisted-record level (SC3's intent is a
    statement about the record/response, not just a single result object —
    the schema-level validator alone cannot catch this)."""
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

    # First advance: real deterministic happy path -- populates the contract.
    first_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert first_response.status_code == 200
    assert first_response.json()["contract"]["text"]

    # Second advance: an injected/overridden runner returns an escalation
    # result for the SAME engagement (e.g. a live-path retry that escalates).
    def _escalating_runner(job):
        return ProposalContractResult(needs_human_input=True, question="q?")

    app.dependency_overrides[get_proposal_runner] = lambda: _escalating_runner
    try:
        second_response = client.post(
            f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
        )
    finally:
        del app.dependency_overrides[get_proposal_runner]

    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["proposal"]["needs_human_input"] is True
    assert second_body["contract"] is None

    get_response = client.get(f"/engagements/{engagement_id}")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["proposal"]["needs_human_input"] is True
    assert get_body["contract"] is None
