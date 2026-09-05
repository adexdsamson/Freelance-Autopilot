"""D-03/D-06(b): the TriageRunner DI seam -- deterministic path is pure
Python (no Agent/Bedrock), env flag selects the live path."""
from agents.triage_runner import (
    _deterministic_triage_runner,
    _supervisor_triage_runner,
    get_triage_runner,
)
from models.engagement_record import JobSlice, TriageSlice


def test_deterministic_triage_runner_is_pure_python():
    job = JobSlice(title="t", description="Simple static site, no red flags", budget=500.0)

    first = _deterministic_triage_runner(job)
    second = _deterministic_triage_runner(job)

    assert isinstance(first, TriageSlice)
    assert first == second  # stable across repeated calls, same input


def test_deterministic_triage_runner_applies_on_clean_job():
    job = JobSlice(title="t", description="Standard React build, clear scope", budget=2000.0)
    result = _deterministic_triage_runner(job)
    assert result.verdict == "apply"


def test_deterministic_triage_runner_skips_below_budget_floor():
    """Placeholder skip-branch coverage (review warning): a below-floor budget
    fires the kill-switch → skip verdict."""
    job = JobSlice(title="t", description="fine scope", budget=10.0)
    result = _deterministic_triage_runner(job)
    assert result.verdict == "skip"
    assert "budget" in result.reasoning.lower()


def test_deterministic_triage_runner_skips_on_red_flag_keyword():
    """Placeholder skip-branch coverage (review warning): a red-flag keyword in
    the description fires the kill-switch → skip verdict, even with a fine budget."""
    job = JobSlice(title="t", description="unpaid trial task, exposure only", budget=5000.0)
    result = _deterministic_triage_runner(job)
    assert result.verdict == "skip"
    assert "keyword" in result.reasoning.lower()


def test_get_triage_runner_selects_supervisor_when_env_set(monkeypatch):
    monkeypatch.setenv("TRIAGE_BACKEND", "supervisor")
    assert get_triage_runner() is _supervisor_triage_runner


def test_get_triage_runner_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    assert get_triage_runner() is _deterministic_triage_runner
