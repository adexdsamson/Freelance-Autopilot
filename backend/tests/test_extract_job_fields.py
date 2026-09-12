"""Covers TRI-01: raw pasted job text -> structured fields.

Entirely deterministic -- `extract_job_fields` makes no model call, so none
of this needs credentials. The regression tests below each guard a specific
misparse that would silently corrupt the gate's decision downstream.
"""
import pytest
from pydantic import ValidationError

from models.triage import ExtractedJobFields
from tests.job_fixtures import ALL_JOBS, load_job
from tools.triage_tools import extract_job_fields


@pytest.mark.parametrize("name", ALL_JOBS)
def test_every_fixture_yields_a_valid_extracted_fields_object(name):
    fields = ExtractedJobFields.model_validate(extract_job_fields(load_job(name)))
    assert fields.title.strip()
    assert fields.description.strip()


def test_title_is_the_first_line_and_description_excludes_it():
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("strong_fixed_apply"))
    )
    assert fields.title == "Senior React Developer to Rebuild SaaS Analytics Dashboard"
    assert fields.title not in fields.description
    assert "TanStack Query" in fields.description


def test_fixed_price_budget_and_full_client_stats_are_parsed():
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("strong_fixed_apply"))
    )
    assert fields.budget == 8_500.0
    assert fields.budget_type == "fixed"
    assert fields.client_stats.total_spend == 142_000.0  # "$142K" expanded
    assert fields.client_stats.hire_rate == pytest.approx(0.89)
    assert fields.client_stats.hires == 45
    assert fields.client_stats.jobs_posted == 132
    assert fields.client_stats.payment_verified is True


def test_hourly_rate_is_not_misread_as_a_fixed_budget():
    """Regression: "$95/hr" read as a $95 fixed budget would hard-reject a
    well-paid contract against the $500 fixed floor."""
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("strong_hourly_apply"))
    )
    assert fields.budget == 95.0
    assert fields.budget_type == "hourly"


def test_client_total_spend_is_not_misread_as_the_job_budget():
    """Regression: the client-history block carries the largest dollar figure
    in a typical posting, so a naive first-$-wins scan picks it up as the
    budget and every job looks generously funded."""
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("weak_client_stats"))
    )
    assert fields.budget == 4_200.0
    assert fields.client_stats.total_spend == 180.0


def test_unverified_payment_is_not_read_as_verified():
    """Regression: "payment method not verified" contains "payment method
    verified" as a substring, so negation must be tested first."""
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("weak_client_stats"))
    )
    assert fields.client_stats.payment_verified is False


def test_absent_metadata_stays_none_rather_than_defaulting_to_zero():
    """A posting that states nothing must not look like a client who has
    spent $0 at a 0% hire rate -- that is a hard reject, not an unknown."""
    fields = ExtractedJobFields.model_validate(
        extract_job_fields(load_job("sparse_no_metadata"))
    )
    assert fields.budget is None
    assert fields.budget_type == "unknown"
    assert fields.client_stats.total_spend is None
    assert fields.client_stats.hire_rate is None
    assert fields.client_stats.payment_verified is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A job\nEst. Budget: $1,250", 1_250.0),
        ("A job\nBudget: $3.5K", 3_500.0),
        ("A job\nFixed-price - Est. Budget: $12,000", 12_000.0),
        ("A job\nPays $2,000 on completion", 2_000.0),
    ],
)
def test_budget_amount_formats(raw, expected):
    assert extract_job_fields(raw)["budget"] == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A job\nHourly - $75/hr", 75.0),
        ("A job\n$60 per hour", 60.0),
        ("A job\nHourly: $40 - $70/hr", 40.0),  # conservative: lower bound
    ],
)
def test_hourly_rate_formats(raw, expected):
    fields = extract_job_fields(raw)
    assert fields["budget"] == expected
    assert fields["budget_type"] == "hourly"


def test_impossible_hire_rate_is_clamped_rather_than_raising():
    """A posting claiming ">100% hire rate" must not blow up ClientStats'
    le=1.0 bound mid-demo."""
    fields = extract_job_fields("A job\nAbout the client\n120% hire rate")
    assert fields["client_stats"]["hire_rate"] == 1.0


def test_empty_text_raises_rather_than_producing_an_empty_record():
    with pytest.raises(ValueError):
        extract_job_fields("   \n  \n ")


def test_extracted_fields_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ExtractedJobFields(title="t", description="d", unexpected="x")
