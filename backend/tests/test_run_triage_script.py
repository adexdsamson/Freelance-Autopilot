"""Covers the standalone runner that makes Phase 2 success criterion 4
executable. Like Phase 1's smoke scripts, `main()` must return an exit code
rather than ending a demo in a traceback, and must never echo a raw AWS error
message (T-01-02).
"""
import pytest

from scripts import run_triage as runner
from tools import triage_tools


@pytest.fixture(autouse=True)
def forbid_llm(monkeypatch):
    """Every case here uses a gate-rejected fixture or fails before Bedrock,
    so a model client must never be constructed."""

    def _explode(*args, **kwargs):
        raise AssertionError("the runner reached Bedrock unexpectedly")

    monkeypatch.setattr(triage_tools, "Agent", _explode)
    monkeypatch.setattr(triage_tools, "BedrockModel", _explode)


def test_list_prints_every_fixture(capsys):
    assert runner.main(["--list"]) == 0
    listed = capsys.readouterr().out.split()
    assert "strong_fixed_apply" in listed
    assert "below_budget_floor" in listed


def test_gate_rejected_fixture_prints_a_triage_result_and_exits_zero(capsys):
    assert runner.main(["below_budget_floor"]) == 0
    printed = capsys.readouterr().out
    assert '"verdict": "skip"' in printed
    assert '"extracted_fields"' in printed


def test_unknown_fixture_fails_readably(capsys):
    assert runner.main(["no_such_fixture"]) == 1
    assert "unknown fixture" in capsys.readouterr().err


def test_missing_file_fails_readably(capsys):
    assert runner.main(["--file", "/nonexistent/posting.txt"]) == 1
    assert "no such file" in capsys.readouterr().err


def test_file_input_is_triaged(tmp_path, capsys):
    posting = tmp_path / "posting.txt"
    posting.write_text("Cheap Logo Job\nEst. Budget: $40\nNeed a logo.")
    assert runner.main(["--file", str(posting)]) == 0
    assert '"verdict": "skip"' in capsys.readouterr().out


def test_no_arguments_exits_with_usage_error():
    with pytest.raises(SystemExit) as excinfo:
        runner.main([])
    assert excinfo.value.code == 2


def test_unexpected_failure_never_leaks_the_underlying_error_message(monkeypatch, capsys):
    secret = "AKIAEXAMPLESECRET-do-not-print"

    def _raise(_raw_text):
        raise RuntimeError(f"boom {secret}")

    monkeypatch.setattr(runner, "run_triage", _raise)

    assert runner.main(["strong_fixed_apply"]) == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
    assert secret not in captured.err
    assert secret not in captured.out
