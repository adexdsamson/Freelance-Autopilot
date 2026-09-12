"""Covers TRI-02 and Phase 2 success criterion 2: the deterministic gate
rejects or flags a fixture job that fails the budget floor, contains a
red-flag phrase, or has weak client spend/hire-rate stats -- verified with no
LLM call.

"No LLM call" is enforced, not assumed: the autouse `forbid_llm` fixture
replaces `Agent` and `BedrockModel` in the tools module with something that
raises on construction, so any accidental model call inside the gate fails
the suite loudly instead of quietly costing tokens (and requiring AWS
credentials to run CI).
"""
import pytest

from models.triage import ExtractedJobFields, KillSwitchResult
from tests.job_fixtures import GATE_PASSING_JOBS, HARD_REJECT_JOBS, load_job
from tools import triage_tools
from tools.triage_config import (
    MIN_CLIENT_HIRE_RATE,
    MIN_CLIENT_SPEND_USD,
    MIN_FIXED_BUDGET_USD,
    MIN_HOURLY_RATE_USD,
    SCORE_WEIGHTS,
)
from tools.triage_tools import extract_job_fields, kill_switch_check


@pytest.fixture(autouse=True)
def forbid_llm(monkeypatch):
    def _explode(*args, **kwargs):
        raise AssertionError(
            "the deterministic gate must never construct an LLM client (TRI-02)"
        )

    monkeypatch.setattr(triage_tools, "Agent", _explode)
    monkeypatch.setattr(triage_tools, "BedrockModel", _explode)


def gate_for(name: str) -> KillSwitchResult:
    return KillSwitchResult.model_validate(
        kill_switch_check(extract_job_fields(load_job(name)))
    )


def gate_for_fields(**kwargs) -> KillSwitchResult:
    defaults = {"title": "A job", "description": "Some work", "budget_type": "fixed"}
    fields = ExtractedJobFields(**{**defaults, **kwargs})
    return KillSwitchResult.model_validate(kill_switch_check(fields.model_dump()))


@pytest.mark.parametrize("name", HARD_REJECT_JOBS)
def test_disqualifying_fixtures_do_not_pass_the_gate(name):
    gate = gate_for(name)
    assert gate.passed is False
    assert gate.rejections


@pytest.mark.parametrize("name", GATE_PASSING_JOBS)
def test_viable_fixtures_pass_the_gate(name):
    gate = gate_for(name)
    assert gate.passed is True
    assert gate.rejections == []


def test_budget_below_the_fixed_floor_is_rejected():
    gate = gate_for("below_budget_floor")
    assert gate.passed is False
    assert any("below the" in r and "floor" in r for r in gate.rejections)


def test_red_flag_phrase_is_rejected_even_when_everything_else_is_strong():
    """The unpaid-test fixture has a $6,000 budget and a verified client with
    a 66% hire rate -- only the phrase disqualifies it."""
    gate = gate_for("red_flag_unpaid_test")
    assert gate.passed is False
    assert gate.rejections == ["posting contains red-flag phrase 'unpaid test'"]


def test_red_flag_matching_is_case_insensitive():
    gate = gate_for_fields(
        description="We require an UNPAID TEST task first.", budget=5_000.0
    )
    assert gate.passed is False
    assert any("unpaid test" in r for r in gate.rejections)


def test_weak_client_spend_and_hire_rate_are_both_rejected():
    gate = gate_for("weak_client_stats")
    assert gate.passed is False
    assert len(gate.rejections) == 2
    assert any("spent only" in r for r in gate.rejections)
    assert any("hire rate" in r for r in gate.rejections)


def test_hourly_rate_is_measured_against_the_hourly_floor_not_the_fixed_one():
    """Regression guarding the gate's half of the fixed-vs-hourly split: $95
    is far below the $500 fixed floor but well above the hourly floor."""
    gate = gate_for_fields(budget=95.0, budget_type="hourly")
    assert gate.passed is True
    assert MIN_HOURLY_RATE_USD < 95.0 < MIN_FIXED_BUDGET_USD


def test_hourly_rate_below_the_hourly_floor_is_rejected():
    gate = gate_for_fields(budget=12.0, budget_type="hourly")
    assert gate.passed is False
    assert any("/hr floor" in r for r in gate.rejections)


def test_thin_but_viable_client_is_flagged_rather_than_rejected():
    """The distinction the two-tier ladder exists for: a small client is a
    concern for the scorecard to weigh, not a disqualification."""
    gate = gate_for("thin_client_flagged")
    assert gate.passed is True
    assert gate.rejections == []
    assert any("thin" in f for f in gate.flags)
    assert any("weak" in f for f in gate.flags)


def test_missing_metadata_is_flagged_and_never_silently_passes():
    gate = gate_for("sparse_no_metadata")
    assert gate.passed is True
    assert any("budget is not stated" in f for f in gate.flags)
    assert any("total spend is not stated" in f for f in gate.flags)
    assert any("hire rate is not stated" in f for f in gate.flags)


def test_a_fully_healthy_posting_raises_nothing_at_all():
    gate = gate_for("strong_fixed_apply")
    assert gate.passed is True
    assert gate.rejections == []
    assert gate.flags == []


def test_unverified_payment_is_a_flag_not_a_rejection():
    gate = gate_for_fields(budget=5_000.0, client_stats={"payment_verified": False})
    assert gate.passed is True
    assert "client payment method is not verified" in gate.flags


@pytest.mark.parametrize(
    ("spend", "hire_rate"),
    [
        (MIN_CLIENT_SPEND_USD, MIN_CLIENT_HIRE_RATE),  # exactly at the floor
        (MIN_CLIENT_SPEND_USD + 0.01, MIN_CLIENT_HIRE_RATE + 0.01),
    ],
)
def test_client_floors_are_inclusive_lower_bounds(spend, hire_rate):
    """At the floor is acceptable; only strictly below is a rejection."""
    gate = gate_for_fields(
        budget=5_000.0,
        client_stats={"total_spend": spend, "hire_rate": hire_rate},
    )
    assert gate.rejections == []


def test_budget_exactly_at_the_fixed_floor_is_accepted():
    gate = gate_for_fields(budget=MIN_FIXED_BUDGET_USD)
    assert not any("floor" in r for r in gate.rejections)


def test_score_weights_sum_to_one():
    """Guards the composite's 0-100 range: weights that do not sum to 1.0
    silently rescale every score in the system."""
    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)
