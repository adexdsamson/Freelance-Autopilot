"""Covers TRI-03: the scorecard produces sub-scores, a composite and
reasoning for a fixture job's fit, competition and rate reasonableness.

The Bedrock call is stubbed. That is not a shortcut around the requirement --
it is the only way to assert the parts that must be *deterministic* (the
composite arithmetic, the explicit model/region/temperature wiring, and the
fact that gate flags actually reach the prompt) independently of what a live
model happens to answer. A real Bedrock call is covered by Phase 1's
connectivity smoke test, which fails fast and readably without credentials.
"""
import pytest

from models.triage import Scorecard, ScorecardJudgment
from tests.job_fixtures import load_job
from tools import triage_tools
from tools.triage_tools import (
    SCORECARD_TEMPERATURE,
    _composite_score,
    extract_job_fields,
    llm_scorecard,
)


class FakeAgent:
    """Records how it was built and what it was asked, then answers fixedly."""

    last_instance = None

    def __init__(self, *, model=None, system_prompt=None):
        self.model = model
        self.system_prompt = system_prompt
        self.structured_output_calls = []
        FakeAgent.last_instance = self

    def structured_output(self, output_model, prompt):
        self.structured_output_calls.append((output_model, prompt))
        return ScorecardJudgment(
            fit_score=8.0,
            competition_score=6.0,
            rate_reasonableness_score=7.0,
            reasoning="Clear scope and a well-funded client.",
        )


class FakeBedrockModel:
    last_kwargs = None

    def __init__(self, **kwargs):
        FakeBedrockModel.last_kwargs = kwargs


@pytest.fixture(autouse=True)
def stub_bedrock(monkeypatch):
    monkeypatch.setattr(triage_tools, "Agent", FakeAgent)
    monkeypatch.setattr(triage_tools, "BedrockModel", FakeBedrockModel)


def score_fixture(name: str, flags=None) -> Scorecard:
    fields = extract_job_fields(load_job(name))
    return Scorecard.model_validate(llm_scorecard(fields, flags))


def test_scorecard_returns_all_three_dimensions_plus_reasoning():
    card = score_fixture("strong_fixed_apply")
    assert card.fit_score == 8.0
    assert card.competition_score == 6.0
    assert card.rate_reasonableness_score == 7.0
    assert card.reasoning


def test_composite_score_is_the_weighted_blend_of_the_sub_scores():
    # fit 8*0.50 + competition 6*0.25 + rate 7*0.25 = 7.25 -> 72.5 / 100
    card = score_fixture("strong_fixed_apply")
    assert card.score == pytest.approx(72.5)


@pytest.mark.parametrize(
    ("fit", "competition", "rate", "expected"),
    [
        (0.0, 0.0, 0.0, 0.0),
        (10.0, 10.0, 10.0, 100.0),
        (6.0, 6.0, 6.0, 60.0),
        (9.0, 3.0, 5.0, 65.0),
    ],
)
def test_composite_score_spans_the_full_0_to_100_range(fit, competition, rate, expected):
    judgment = ScorecardJudgment(
        fit_score=fit,
        competition_score=competition,
        rate_reasonableness_score=rate,
        reasoning="x",
    )
    assert _composite_score(judgment) == pytest.approx(expected)


def test_composite_is_computed_in_code_not_requested_from_the_model():
    """The model is asked for ScorecardJudgment, which has no `score` field --
    that is what makes identical sub-scores always yield one identical total
    (DEMO-02)."""
    score_fixture("strong_fixed_apply")
    output_model, _ = FakeAgent.last_instance.structured_output_calls[0]
    assert output_model is ScorecardJudgment
    assert "score" not in ScorecardJudgment.model_fields


def test_bedrock_model_is_constructed_explicitly_with_pinned_id_region_and_zero_temperature():
    """D-06: the model id and region stay visible in code, never a bare
    model-id string handed to Agent(model=...)."""
    score_fixture("strong_fixed_apply")
    kwargs = FakeBedrockModel.last_kwargs
    assert kwargs["model_id"] == triage_tools.MODEL_ID
    assert kwargs["region_name"] == triage_tools.REGION
    assert kwargs["temperature"] == SCORECARD_TEMPERATURE == 0.0
    assert isinstance(FakeAgent.last_instance.model, FakeBedrockModel)


def test_gate_flags_are_passed_to_the_model_as_concerns_it_must_weigh():
    """A flag the scorecard never sees is a flag that changes nothing."""
    score_fixture("thin_client_flagged", flags=["client spend $2,400.00 is thin"])
    _, prompt = FakeAgent.last_instance.structured_output_calls[0]
    assert "CONCERNS:" in prompt
    assert "client spend $2,400.00 is thin" in prompt


def test_absent_flags_render_as_none_rather_than_an_empty_section():
    score_fixture("strong_fixed_apply")
    _, prompt = FakeAgent.last_instance.structured_output_calls[0]
    assert "CONCERNS:\n- none" in prompt


def test_prompt_carries_the_job_and_client_context_the_rubric_needs():
    score_fixture("strong_fixed_apply")
    _, prompt = FakeAgent.last_instance.structured_output_calls[0]
    assert "Senior React Developer" in prompt
    assert "$8,500.00 (fixed)" in prompt
    assert "142000.0" in prompt


def test_system_prompt_defines_all_three_scoring_dimensions():
    score_fixture("strong_fixed_apply")
    system_prompt = FakeAgent.last_instance.system_prompt
    for dimension in ("fit_score", "competition_score", "rate_reasonableness_score"):
        assert dimension in system_prompt
