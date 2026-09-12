"""Covers TRI-04 and Phase 2 success criterion 4: running the Gig Triage
Agent standalone against a fixture job returns
`{ verdict, score, reasoning, extracted_fields }` with no escalation fields
present anywhere in the output.

"Anywhere" is checked structurally, not by eyeballing one happy-path result:
`TriageResult` forbids extras, so the absence of `needs_human_input` /
`question` is enforced by the schema rather than by convention, and the
recursive walk below proves no nested slice reintroduces them either.

Standalone means standalone -- nothing here constructs a Supervisor, touches
FastAPI, or imports the store.
"""
import pytest
from pydantic import ValidationError

from agents.gig_triage_agent import GigTriageAgent, run_triage
from models.triage import ScorecardJudgment, TriageResult
from tests.job_fixtures import GATE_PASSING_JOBS, HARD_REJECT_JOBS, load_job
from tools import triage_tools
from tools.triage_config import APPLY_SCORE_THRESHOLD

ESCALATION_FIELD_NAMES = ("needs_human_input", "question", "escalate", "ask_user")


class FakeAgent:
    """Answers with whatever sub-scores the active test asked for."""

    sub_scores = (8.0, 6.0, 7.0)
    call_count = 0

    def __init__(self, *, model=None, system_prompt=None):
        pass

    def structured_output(self, output_model, prompt):
        FakeAgent.call_count += 1
        fit, competition, rate = FakeAgent.sub_scores
        return ScorecardJudgment(
            fit_score=fit,
            competition_score=competition,
            rate_reasonableness_score=rate,
            reasoning="Scope is clear and the client is well established.",
        )


@pytest.fixture
def stub_scorecard(monkeypatch):
    """Stub the Bedrock hop only. The gate and the parser stay real."""
    FakeAgent.call_count = 0
    FakeAgent.sub_scores = (8.0, 6.0, 7.0)
    monkeypatch.setattr(triage_tools, "Agent", FakeAgent)
    monkeypatch.setattr(triage_tools, "BedrockModel", lambda **kwargs: object())
    return FakeAgent


@pytest.fixture
def forbid_llm(monkeypatch):
    def _explode(*args, **kwargs):
        raise AssertionError("a gate-rejected posting must cost zero model calls")

    monkeypatch.setattr(triage_tools, "Agent", _explode)
    monkeypatch.setattr(triage_tools, "BedrockModel", _explode)


def _walk_keys(value):
    """Every key appearing anywhere in a nested dict/list structure."""
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


# --- The TRI-04 output contract -------------------------------------------


@pytest.mark.parametrize("name", GATE_PASSING_JOBS)
def test_scored_run_returns_exactly_the_four_contract_fields(name, stub_scorecard):
    result = run_triage(load_job(name))
    assert set(result.model_dump()) == {
        "verdict",
        "score",
        "reasoning",
        "extracted_fields",
    }


@pytest.mark.parametrize("name", HARD_REJECT_JOBS + GATE_PASSING_JOBS)
def test_no_escalation_field_appears_anywhere_in_the_output(name, stub_scorecard):
    keys = set(_walk_keys(run_triage(load_job(name)).model_dump()))
    assert keys.isdisjoint(ESCALATION_FIELD_NAMES)


def test_triage_result_schema_structurally_rejects_escalation_fields():
    """Stage 1 is autonomous by construction: even a future caller cannot
    smuggle an escalation field in, because the model forbids extras."""
    valid = {
        "verdict": "apply",
        "score": 70.0,
        "reasoning": "ok",
        "extracted_fields": {"title": "t", "description": "d"},
    }
    assert TriageResult.model_validate(valid)
    for field in ESCALATION_FIELD_NAMES:
        with pytest.raises(ValidationError):
            TriageResult.model_validate({**valid, field: True})


def test_verdict_is_only_ever_apply_or_skip(stub_scorecard):
    for name in HARD_REJECT_JOBS + GATE_PASSING_JOBS:
        assert run_triage(load_job(name)).verdict in ("apply", "skip")


# --- The deterministic gate genuinely gates -------------------------------


@pytest.mark.parametrize("name", HARD_REJECT_JOBS)
def test_gate_rejected_posting_skips_without_any_model_call(name, forbid_llm):
    result = run_triage(load_job(name))
    assert result.verdict == "skip"
    assert result.score == 0.0
    assert "deterministic pre-screen" in result.reasoning


def test_rejection_reasoning_names_the_disqualifying_reason(forbid_llm):
    result = run_triage(load_job("red_flag_unpaid_test"))
    assert "unpaid test" in result.reasoning


def test_gate_rejected_runs_are_byte_identical_across_repeats(forbid_llm):
    """DEMO-02 in miniature: the reject path has no model in it at all, so
    repeated runs must agree exactly."""
    runs = [run_triage(load_job("below_budget_floor")).model_dump() for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_scored_posting_does_reach_the_model(stub_scorecard):
    run_triage(load_job("strong_fixed_apply"))
    assert stub_scorecard.call_count == 1


# --- Verdict threshold ----------------------------------------------------


@pytest.mark.parametrize(
    ("sub_scores", "expected_score", "expected_verdict"),
    [
        ((6.0, 6.0, 6.0), 60.0, "apply"),  # exactly at the threshold
        ((5.9, 5.9, 5.9), 59.0, "skip"),  # just below
        ((10.0, 10.0, 10.0), 100.0, "apply"),
        ((1.0, 1.0, 1.0), 10.0, "skip"),
    ],
)
def test_apply_threshold_is_an_inclusive_lower_bound(
    stub_scorecard, sub_scores, expected_score, expected_verdict
):
    stub_scorecard.sub_scores = sub_scores
    result = run_triage(load_job("strong_fixed_apply"))
    assert result.score == pytest.approx(expected_score)
    assert result.verdict == expected_verdict
    assert (result.score >= APPLY_SCORE_THRESHOLD) is (expected_verdict == "apply")


# --- Reasoning is usable by a human ---------------------------------------


def test_scored_reasoning_reports_every_sub_score_and_the_threshold(stub_scorecard):
    reasoning = run_triage(load_job("strong_fixed_apply")).reasoning
    assert "fit 8/10" in reasoning
    assert "competition 6/10" in reasoning
    assert "rate 7/10" in reasoning
    assert "72.5/100" in reasoning


def test_gate_flags_are_surfaced_in_the_reasoning_of_a_scored_run(stub_scorecard):
    """A concern that changed the score must be visible to the freelancer."""
    reasoning = run_triage(load_job("thin_client_flagged")).reasoning
    assert "Pre-screen concerns weighed:" in reasoning
    assert "thin" in reasoning


def test_clean_posting_reasoning_omits_the_concerns_sentence(stub_scorecard):
    reasoning = run_triage(load_job("strong_fixed_apply")).reasoning
    assert "Pre-screen concerns weighed:" not in reasoning


# --- Extracted fields survive the round trip ------------------------------


def test_extracted_fields_are_returned_alongside_the_verdict(stub_scorecard):
    result = run_triage(load_job("strong_hourly_apply"))
    assert result.extracted_fields.budget == 95.0
    assert result.extracted_fields.budget_type == "hourly"
    assert result.extracted_fields.client_stats.hire_rate == pytest.approx(0.74)


def test_agent_instance_is_reusable_across_engagements(stub_scorecard):
    """The specialist holds no per-run state, so one instance can serve many
    captures -- which is what Phase 3 will do behind a single tool."""
    agent = GigTriageAgent()
    first = agent.run(load_job("strong_fixed_apply"))
    second = agent.run(load_job("strong_fixed_apply"))
    assert first.model_dump() == second.model_dump()


def test_empty_posting_raises_rather_than_returning_a_hollow_verdict():
    with pytest.raises(ValueError):
        run_triage("")
