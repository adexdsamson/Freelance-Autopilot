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


def test_get_triage_runner_selects_supervisor_when_env_set(monkeypatch):
    monkeypatch.setenv("TRIAGE_BACKEND", "supervisor")
    assert get_triage_runner() is _supervisor_triage_runner


def test_get_triage_runner_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("TRIAGE_BACKEND", raising=False)
    assert get_triage_runner() is _deterministic_triage_runner
