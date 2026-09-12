"""D-04/DEMO-01: the fixture loader is pure data (no store import) and its
variant selector produces the two documented creep/clean states."""
import ast
from datetime import date
from pathlib import Path

from fixtures.loader import load_client_thread, load_payment_schedule
from tools.check_scope_creep import CREEP_SIGNAL_PHRASES

REFERENCE_DATE = date(2026, 6, 1)


def test_load_client_thread_creep_variant_contains_a_creep_signal():
    thread = load_client_thread("creep")
    assert isinstance(thread, list) and thread
    assert any(
        any(phrase in message.lower() for phrase in CREEP_SIGNAL_PHRASES)
        for message in thread
    )


def test_load_client_thread_clean_variant_has_no_creep_signal():
    thread = load_client_thread("clean")
    assert isinstance(thread, list) and thread
    for message in thread:
        lowered = message.lower()
        assert not any(phrase in lowered for phrase in CREEP_SIGNAL_PHRASES)


def test_load_payment_schedule_creep_variant_has_one_unpaid_past_due_item():
    schedule = load_payment_schedule("creep")
    assert isinstance(schedule, list) and schedule
    unpaid_past = [
        item
        for item in schedule
        if not item["paid"] and date.fromisoformat(item["due_date"]) < REFERENCE_DATE
    ]
    assert len(unpaid_past) == 1


def test_load_payment_schedule_clean_variant_has_zero_overdue_items():
    schedule = load_payment_schedule("clean")
    assert isinstance(schedule, list) and schedule
    unpaid_past = [
        item
        for item in schedule
        if not item["paid"] and date.fromisoformat(item["due_date"]) < REFERENCE_DATE
    ]
    assert len(unpaid_past) == 0


def test_loader_is_pure_data_no_store_import():
    """DEMO-01: the loader must never import the store, mirroring the
    single-writer guard applied to backend/agents/ and backend/tools/."""
    source = (Path(__file__).resolve().parent.parent / "fixtures" / "loader.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any("store" in alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert "store" not in node.module
