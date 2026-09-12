"""Covers the AgentCore Runtime entrypoint (Phase 8, SC2).

SC2 asks that the Supervisor and specialists, deployed to Runtime, process a
capture-through-advance flow. What is tested here is the routing and the
handler reuse — that a Runtime invocation lands on the SAME api.py handlers
the HTTP transport uses, so the two cannot drift. What is NOT tested, because
no AWS credentials or AgentCore resources were available, is an actual
deployment or a live invocation.
"""
import ast
from pathlib import Path

import pytest

import agentcore_runtime
from agentcore_runtime import handle_invocation
from store.file_engagement_store import FileEngagementStore

CLEAN_JOB = {
    "title": "Rebuild dashboard",
    "description": "React 18 work with a clear acceptance checklist.",
    "budget": 8500.0,
}


@pytest.fixture
def store(tmp_path):
    return FileEngagementStore(base_dir=tmp_path)


def test_capture_creates_a_record_and_returns_a_verdict(store):
    result = handle_invocation({"action": "capture", "job": CLEAN_JOB}, store)
    assert "engagement_id" in result
    assert result["verdict"] in ("apply", "skip")
    assert "error" not in result


def test_capture_then_get_round_trips_through_the_store(store):
    captured = handle_invocation({"action": "capture", "job": CLEAN_JOB}, store)
    fetched = handle_invocation(
        {"action": "get", "engagement_id": captured["engagement_id"]}, store
    )
    assert fetched["engagement_id"] == captured["engagement_id"]
    assert fetched["triage"]["verdict"] == captured["verdict"]


def test_unknown_action_names_the_valid_ones(store):
    result = handle_invocation({"action": "teleport"}, store)
    assert "capture, advance, get" in result["error"]


@pytest.mark.parametrize("payload", [{}, None, {"action": None}])
def test_a_missing_action_is_an_error_not_a_crash(payload, store):
    assert "error" in handle_invocation(payload, store)


def test_a_malformed_job_is_an_error_not_a_traceback(store):
    result = handle_invocation({"action": "capture", "job": {"title": "no desc"}}, store)
    assert "error" in result


def test_a_failure_never_leaks_the_underlying_message(store, monkeypatch):
    secret = "AKIA-do-not-print"

    def explode(**kwargs):
        raise RuntimeError(f"boom {secret}")

    monkeypatch.setattr(agentcore_runtime.api, "capture", explode)
    result = handle_invocation({"action": "capture", "job": CLEAN_JOB}, store)
    assert "RuntimeError" in result["error"]
    assert secret not in result["error"]


def test_get_on_an_unknown_engagement_is_an_error_not_a_crash(store):
    result = handle_invocation(
        {"action": "get", "engagement_id": "00000000-0000-4000-8000-000000000000"},
        store,
    )
    assert "error" in result


def test_module_does_not_import_bedrock_agentcore_at_module_scope():
    """SC3: nothing about Phase 8 may make the local path depend on the
    optional, community-maintained package."""
    tree = ast.parse(Path(agentcore_runtime.__file__).read_text())
    names = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    assert not any(n.startswith("bedrock_agentcore") for n in names)


def test_runtime_reuses_api_handlers_rather_than_reimplementing_them():
    """If the Runtime path grew its own capture logic it could drift from the
    HTTP path — different triage runner, different merge, different store."""
    source = Path(agentcore_runtime.__file__).read_text()
    assert "api.capture(" in source
    assert "api.advance(" in source
    assert "api.get_engagement(" in source
