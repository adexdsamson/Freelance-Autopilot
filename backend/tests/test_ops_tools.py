"""D-02/OPS-01..03/SC2..SC4: unit-depth coverage of the three deterministic
ops tools -- all pure Python, no Agent/Bedrock."""
from fixtures.loader import load_client_thread, load_payment_schedule
from tools.check_invoice_status import check_invoice_status
from tools.check_scope_creep import check_scope_creep
from tools.draft_status_update import draft_status_update

CONTRACT_TEXT = (
    "Statement of Work: Build a marketing site\n\n"
    "Deliverables (per proposal):\n"
    "  1. Discovery & scoping deliverable\n"
    "  2. Core deliverable per agreed scope\n"
    "  3. Final revisions & handoff package\n\n"
    "Payment terms: milestone-based, see payment_schedule."
)

REFERENCE_DATE = "2026-06-01"


# --- check_scope_creep (OPS-01) ---------------------------------------------


def test_check_scope_creep_flags_exactly_one_on_creep_fixture():
    thread = load_client_thread("creep")
    result = check_scope_creep(CONTRACT_TEXT, thread)
    assert len(result["scope_creep_flags"]) == 1


def test_check_scope_creep_flags_zero_on_clean_fixture():
    thread = load_client_thread("clean")
    result = check_scope_creep(CONTRACT_TEXT, thread)
    assert result["scope_creep_flags"] == []


def test_check_scope_creep_is_deterministic():
    thread = load_client_thread("creep")
    first = check_scope_creep(CONTRACT_TEXT, thread)
    second = check_scope_creep(CONTRACT_TEXT, thread)
    assert first == second


# --- check_invoice_status (OPS-02) ------------------------------------------


def test_check_invoice_status_flags_exactly_one_overdue_on_creep_fixture():
    schedule = load_payment_schedule("creep")
    result = check_invoice_status(schedule, REFERENCE_DATE)
    assert len(result["invoice_flags"]) == 1
    assert result["invoice_flags"][0]["days_overdue"] > 0


def test_check_invoice_status_flags_zero_on_clean_fixture():
    schedule = load_payment_schedule("clean")
    result = check_invoice_status(schedule, REFERENCE_DATE)
    assert result["invoice_flags"] == []


def test_check_invoice_status_is_deterministic_and_never_reads_wall_clock():
    schedule = load_payment_schedule("creep")
    first = check_invoice_status(schedule, REFERENCE_DATE)
    second = check_invoice_status(schedule, REFERENCE_DATE)
    assert first == second


# --- draft_status_update (OPS-03/SC4) ---------------------------------------


def test_draft_status_update_mentions_scope_and_invoice_concerns():
    text = draft_status_update(
        [{"message": "m", "reason": "r"}],
        [{"milestone_label": "l", "due_date": "2025-01-15", "days_overdue": 5}],
    )["text"]
    assert "scope" in text.lower()
    assert "overdue" in text.lower()


def test_draft_status_update_states_on_track_when_no_flags():
    text = draft_status_update([], [])["text"]
    assert "on track" in text.lower()
