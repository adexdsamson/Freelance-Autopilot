"""DEMO-02/SC1/D-01: one-command demo entrypoint — drives capture -> proposal
-> ops end-to-end, in-process, via `fastapi.testclient.TestClient(app)`.

Invoke as `cd backend && python3 -m scripts.run_demo [--fixture creep|clean]
[--ambiguous]` — the bare-script form (`python3 backend/scripts/run_demo.py`
or `python3 scripts/run_demo.py`) raises `ModuleNotFoundError: No module
named 'api'` because `api.py`'s bare-name imports only resolve when
`backend/` itself is on `sys.path`, which `-m` module invocation (cwd on
sys.path) provides and a bare script invocation does not (RESEARCH.md
Pitfall 2).

This script does NOT do two things:
  1. It does not add a second Engagement Record store writer (REC-03) — it
     reaches persistence ONLY through `api.py`'s HTTP routes via TestClient,
     never by importing `store` or any `store.*` module.
  2. It does not require AWS credentials by default — the deterministic
     placeholder backends (TRIAGE_BACKEND/PROPOSAL_BACKEND/OPS_BACKEND all
     unset) run fully offline; setting `*_BACKEND=supervisor` would exercise
     the live Bedrock path, which this script never sets on its own.
"""
from __future__ import annotations

import argparse

from fastapi.testclient import TestClient

from api import app

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


def build_client() -> TestClient:
    """Construct a TestClient over the UNMODIFIED FastAPI app — no
    dependency_overrides. This exercises the real default FileEngagementStore
    under backend/data/engagements/ (gitignored), so the demo behaves like a
    real run, not a test double (D-01/Pattern 1)."""
    return TestClient(app)


def run_pipeline(client: TestClient, fixture: str, ambiguous: bool) -> None:
    """Run capture -> proposal -> ops and print the progression. Mirrors the
    verified sequence in test_advance_endpoint.py (lines 106-176)."""
    job = AMBIGUOUS_JOB if ambiguous else CLEAR_SCOPE_JOB

    print(f"=== STEP 1: POST /capture ({'ambiguous' if ambiguous else 'clear-scope'} job) ===")
    capture_response = client.post("/capture", json=job)
    capture_response.raise_for_status()
    capture_body = capture_response.json()
    engagement_id = capture_body["engagement_id"]
    print(f"triage verdict: {capture_body['verdict']}")
    print(f"triage score:   {capture_body['score']}")
    print(f"triage reasoning: {capture_body['reasoning']}")

    print("\n=== STEP 2: POST /engagements/{id}/advance?stage=proposal ===")
    proposal_response = client.post(
        f"/engagements/{engagement_id}/advance", params={"stage": "proposal"}
    )
    proposal_response.raise_for_status()
    proposal_body = proposal_response.json()
    proposal = proposal_body["proposal"]
    contract = proposal_body["contract"]

    if proposal["needs_human_input"]:
        print(f"ESCALATION — needs_human_input=True")
        print(f"question: {proposal['question']}")
        print(
            "\nOps stage skipped: no signed contract exists (escalated proposal)."
        )
        print(f"SUMMARY scenario=ambiguous triage_verdict={capture_body['verdict']} proposal=needs_human_input")
        return

    print(f"proposal text: {proposal['text']}")
    print(f"contract text: {contract['text']}")
    print(f"payment schedule: {contract['payment_schedule']}")

    print(f"\n=== STEP 3: POST /engagements/{{id}}/advance?stage=ops&fixture={fixture} ===")
    ops_response = client.post(
        f"/engagements/{engagement_id}/advance",
        params={"stage": "ops", "fixture": fixture},
    )
    ops_response.raise_for_status()
    ops_body = ops_response.json()
    ops = ops_body["ops"]
    ops_cards = len(ops["scope_creep_flags"]) + len(ops["invoice_flags"])
    print(f"status updates: {ops['status_updates']}")
    print(f"scope-creep flags: {ops['scope_creep_flags']}")
    print(f"invoice flags: {ops['invoice_flags']}")

    print(f"\nSUMMARY fixture={fixture} triage_verdict={capture_body['verdict']} ops_cards={ops_cards}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Freelance Autopilot demo pipeline end-to-end "
            "(capture -> proposal -> ops), in-process, no live server."
        )
    )
    parser.add_argument(
        "--fixture",
        choices=["creep", "clean"],
        default="creep",
        help="Which ops fixture variant to run (default: creep).",
    )
    parser.add_argument(
        "--ambiguous",
        action="store_true",
        help="Use the ambiguous-scope job instead of the clear-scope job "
        "(deterministically escalates at the proposal stage).",
    )
    args = parser.parse_args()

    client = build_client()
    run_pipeline(client, args.fixture, args.ambiguous)


if __name__ == "__main__":
    main()
