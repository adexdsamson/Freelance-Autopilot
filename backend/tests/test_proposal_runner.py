"""D-03/D-06(b)/PROP-01..04/SC2/SC3: unit-depth coverage of the three
deterministic tools, the ProposalRunner DI seam, and ProposalContractResult's
mutual-exclusivity validator -- all pure Python, no Agent/Bedrock."""
import pytest

from agents.proposal_runner import (
    _deterministic_proposal_runner,
    _supervisor_proposal_runner,
    get_proposal_runner,
)
from models.engagement_record import JobSlice, PaymentMilestone, ProposalContractResult
from tools.check_scope_clarity import check_scope_clarity
from tools.draft_contract import draft_contract
from tools.draft_proposal import draft_proposal

CLEAR_DESCRIPTION = (
    "Standard React build with a clear scope, three deliverable phases, "
    "and a deadline in 6 weeks."
)
AMBIGUOUS_DESCRIPTION = "Something small, not much detail here."


# --- draft_proposal (PROP-01) ---------------------------------------------


def test_draft_proposal_mentions_three_phases_and_budget():
    result = draft_proposal("Build a site", CLEAR_DESCRIPTION, 2000.0)
    text = result["proposal_text"]
    assert "Phase 1" in text
    assert "Phase 2" in text
    assert "Phase 3" in text
    assert "2,000.00" in text


def test_draft_proposal_is_deterministic():
    first = draft_proposal("Build a site", CLEAR_DESCRIPTION, 2000.0)
    second = draft_proposal("Build a site", CLEAR_DESCRIPTION, 2000.0)
    assert first == second


# --- draft_contract (PROP-02) ----------------------------------------------


def test_draft_contract_enumerates_deliverables():
    result = draft_contract("Build a site", CLEAR_DESCRIPTION, "proposal text", 2000.0)
    text = result["contract_text"]
    assert "Deliverables" in text
    assert "1." in text and "2." in text and "3." in text


def test_draft_contract_is_deterministic():
    first = draft_contract("Build a site", CLEAR_DESCRIPTION, "proposal text", 2000.0)
    second = draft_contract("Build a site", CLEAR_DESCRIPTION, "proposal text", 2000.0)
    assert first == second


# --- payment_schedule (PROP-03) --------------------------------------------


@pytest.mark.parametrize(
    "budget",
    [
        2000.0,  # coincidentally exact under naive independent rounding
        999.99,  # WR-01: naive independent rounding drifts by +$0.01 here
        333.33,  # coincidentally exact under naive independent rounding
    ],
)
def test_draft_contract_payment_schedule_items_have_required_keys_and_sum_to_budget(budget):
    result = draft_contract("Build a site", CLEAR_DESCRIPTION, "proposal text", budget)
    schedule = result["payment_schedule"]
    assert len(schedule) == 3
    for item in schedule:
        assert set(item.keys()) == {"label", "amount", "due_marker"}
    assert round(sum(item["amount"] for item in schedule), 2) == round(budget, 2)


def test_proposal_contract_result_coerces_payment_schedule_into_payment_milestones():
    result = ProposalContractResult(
        proposal_text="p",
        contract_text="c",
        payment_schedule=[
            {"label": "On signing", "amount": 600.0, "due_marker": "on_signing"},
            {"label": "On delivery", "amount": 1000.0, "due_marker": "on_delivery"},
            {"label": "Final handoff", "amount": 400.0, "due_marker": "net_15"},
        ],
    )
    assert all(isinstance(item, PaymentMilestone) for item in result.payment_schedule)


# --- scope-clarity gate (PROP-04) ------------------------------------------


@pytest.mark.parametrize(
    ("budget", "description", "expected_missing"),
    [
        (None, CLEAR_DESCRIPTION, {"budget"}),
        (2000.0, "No timing words at all, just deliverable phases and milestones.", {"timeline"}),
        (2000.0, "Due in 6 weeks, by next month, asap.", {"deliverables"}),
        (2000.0, "Something small.", {"timeline", "deliverables"}),
    ],
)
def test_check_scope_clarity_cites_exact_missing_fields(budget, description, expected_missing):
    result = check_scope_clarity(budget, description)
    assert result["clear"] is False
    for field in expected_missing:
        assert field in result["question"]


def test_check_scope_clarity_clear_when_budget_timeline_and_deliverables_present():
    result = check_scope_clarity(2000.0, CLEAR_DESCRIPTION)
    assert result == {"clear": True, "question": None}


# --- ambiguous runner path (SC2) -------------------------------------------


def test_deterministic_proposal_runner_escalates_on_ambiguous_job_without_raising():
    job = JobSlice(title="t", description=AMBIGUOUS_DESCRIPTION, budget=None)
    result = _deterministic_proposal_runner(job)
    assert isinstance(result, ProposalContractResult)
    assert result.needs_human_input is True
    assert result.question
    assert result.contract_text is None


def test_deterministic_proposal_runner_happy_on_clear_job():
    job = JobSlice(title="t", description=CLEAR_DESCRIPTION, budget=2000.0)
    result = _deterministic_proposal_runner(job)
    assert result.needs_human_input is False
    assert result.proposal_text
    assert result.contract_text
    assert result.payment_schedule


# --- exclusivity (SC3) ------------------------------------------------------


def test_exclusivity_rejects_both_populated():
    with pytest.raises(ValueError):
        ProposalContractResult(
            needs_human_input=True,
            question="q",
            contract_text="x",
        )


def test_exclusivity_rejects_neither_populated():
    with pytest.raises(ValueError):
        ProposalContractResult(needs_human_input=False)


def test_exclusivity_accepts_valid_happy_and_escalation_constructions():
    happy = ProposalContractResult(
        proposal_text="p",
        contract_text="c",
        payment_schedule=[{"label": "l", "amount": 1.0, "due_marker": "on_signing"}],
    )
    assert happy.needs_human_input is False

    escalation = ProposalContractResult(needs_human_input=True, question="q?")
    assert escalation.needs_human_input is True


# --- env selection -----------------------------------------------------------


def test_get_proposal_runner_selects_supervisor_when_env_set(monkeypatch):
    monkeypatch.setenv("PROPOSAL_BACKEND", "supervisor")
    assert get_proposal_runner() is _supervisor_proposal_runner


def test_get_proposal_runner_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("PROPOSAL_BACKEND", raising=False)
    assert get_proposal_runner() is _deterministic_proposal_runner
