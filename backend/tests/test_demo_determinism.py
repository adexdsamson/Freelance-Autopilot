"""DEMO-02/SC1/SC2/D-02/D-07(a)(b): proves the demo pipeline is
deterministic across repeated runs and that one run populates every stage
slice.

Uses the conftest tmp-path-isolated `client` fixture (never the real
backend/data/engagements/ store — that's run_demo.py's job, by design).

Excludes two volatile fields from the equality comparison (RESEARCH.md
Pitfall 1):
  - engagement_id: a fresh UUID per run (models/engagement_record.py:139)
  - ops.invoice_flags[].days_overdue: derived from date.today() in
    backend/tools/check_invoice_status.py — stable within a single run but
    not guaranteed stable across a day boundary if the 3 runs were ever
    split across midnight.
Every other decision field (triage.verdict/score/reasoning,
proposal.text/needs_human_input/question, contract.text/payment_schedule,
ops.status_updates[].text, ops.scope_creep_flags,
ops.invoice_flags[].milestone_label/due_date) is fully content-deterministic
and IS compared.
"""
from fastapi.testclient import TestClient

CLEAR_SCOPE_JOB = {
    "title": "Build a marketing site",
    "description": (
        "Standard React build with a clear scope, three deliverable "
        "phases, and a deadline in 6 weeks."
    ),
    "budget": 2000.0,
}

AMBIGUOUS_JOB = {
    "title": "t",
    "description": "Looking for someone to help with ongoing design work.",
    "budget": 500.0,
}


def _curated_decision_fields(ops_body: dict) -> dict:
    """Extract ONLY the deterministic decision fields from an /advance
    (stage=ops) response body, dropping engagement_id entirely and
    stripping days_overdue from each invoice flag (Pitfall 1)."""
    return {
        "triage": ops_body["triage"],
        "proposal": ops_body["proposal"],
        "contract": ops_body["contract"],
        "ops": {
            "status_updates": ops_body["ops"]["status_updates"],
            "scope_creep_flags": ops_body["ops"]["scope_creep_flags"],
            "invoice_flags": [
                {k: v for k, v in flag.items() if k != "days_overdue"}
                for flag in ops_body["ops"]["invoice_flags"]
            ],
        },
    }


def _run_once(client: TestClient, fixture: str) -> dict:
    """Run the full capture -> proposal -> ops sequence once for the given
    fixture variant and return the curated decision-field dict."""
    capture = client.post("/capture", json=CLEAR_SCOPE_JOB)
    assert capture.status_code == 200
    engagement_id = capture.json()["engagement_id"]

    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert proposal_response.status_code == 200

    ops_response = client.post(
        f"/engagements/{engagement_id}/advance",
        params={"stage": "ops", "fixture": fixture},
    )
    assert ops_response.status_code == 200
    return _curated_decision_fields(ops_response.json())


def test_full_fixture_set_is_deterministic_across_three_runs(client):
    """DEMO-02/SC2: running the creep and clean fixture sets three times
    each yields byte-identical curated decision dicts."""
    for fixture in ("creep", "clean"):
        runs = [_run_once(client, fixture) for _ in range(3)]
        assert runs[0] == runs[1] == runs[2]


def test_ambiguous_escalation_is_deterministic_across_three_runs(client):
    """DEMO-02/SC2/D-02: Beat 3's `--ambiguous` proposal-stage escalation
    (AMBIGUOUS_JOB, the same shape run_demo.py uses) is machine-verified
    deterministic across three independent runs, not just manually
    inspected."""
    runs = []
    for _ in range(3):
        capture = client.post("/capture", json=AMBIGUOUS_JOB)
        assert capture.status_code == 200
        eid = capture.json()["engagement_id"]
        resp = client.post(f"/engagements/{eid}/advance", params={"stage": "proposal"})
        assert resp.status_code == 200
        body = resp.json()["proposal"]
        runs.append({"needs_human_input": body["needs_human_input"], "question": body["question"]})
    assert runs[0] == runs[1] == runs[2]


def test_pipeline_populates_all_stage_slices(client):
    """DEMO-02/SC1: one capture -> proposal -> ops run populates every
    stage slice of the Engagement Record."""
    capture = client.post("/capture", json=CLEAR_SCOPE_JOB)
    assert capture.status_code == 200
    engagement_id = capture.json()["engagement_id"]

    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    assert proposal_response.status_code == 200

    ops_response = client.post(
        f"/engagements/{engagement_id}/advance",
        params={"stage": "ops", "fixture": "creep"},
    )
    assert ops_response.status_code == 200

    final_body = client.get(f"/engagements/{engagement_id}").json()
    assert final_body["triage"] is not None
    assert final_body["triage"]["verdict"] in {"apply", "skip"}
    assert final_body["proposal"]["text"]
    assert final_body["contract"] is not None
    assert final_body["contract"]["payment_schedule"]
    assert final_body["ops"]["status_updates"]
