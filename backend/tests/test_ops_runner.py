"""D-03/SC2/SC3: unit-depth coverage of the OpsRunner DI seam -- the
creep/clean variants must yield 2/0 escalation cards through the SAME
conditional code path, never a hardcoded per-variant branch."""
from agents.ops_runner import (
    _deterministic_ops_runner,
    _supervisor_ops_runner,
    get_ops_runner,
)
from models.engagement_record import ContractSlice, OpsResult

CONTRACT = ContractSlice(
    text=(
        "Statement of Work: Build a marketing site\n\n"
        "Deliverables (per proposal):\n"
        "  1. Discovery & scoping deliverable\n"
        "  2. Core deliverable per agreed scope\n"
        "  3. Final revisions & handoff package\n\n"
        "Payment terms: milestone-based, see payment_schedule."
    )
)


def _card_count(result: OpsResult) -> int:
    return len(result.scope_creep_flags) + len(result.invoice_flags)


def test_deterministic_ops_runner_creep_fixture_yields_two_cards():
    result = _deterministic_ops_runner(CONTRACT, "creep")
    assert isinstance(result, OpsResult)
    assert _card_count(result) == 2


def test_deterministic_ops_runner_clean_fixture_yields_zero_cards():
    result = _deterministic_ops_runner(CONTRACT, "clean")
    assert isinstance(result, OpsResult)
    assert _card_count(result) == 0


def test_get_ops_runner_selects_supervisor_when_env_set(monkeypatch):
    monkeypatch.setenv("OPS_BACKEND", "supervisor")
    assert get_ops_runner() is _supervisor_ops_runner


def test_get_ops_runner_defaults_to_deterministic(monkeypatch):
    monkeypatch.delenv("OPS_BACKEND", raising=False)
    assert get_ops_runner() is _deterministic_ops_runner
