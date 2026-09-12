"""Loader for the raw job-posting fixtures under tests/fixtures/jobs/.

A plain importable module rather than a pytest fixture because
`@pytest.mark.parametrize` needs these values at collection time.
"""
from pathlib import Path

JOBS_DIR = Path(__file__).parent / "fixtures" / "jobs"

# Every fixture, by the gate outcome it is built to exercise.
HARD_REJECT_JOBS = (
    "below_budget_floor",
    "red_flag_unpaid_test",
    "weak_client_stats",
)
GATE_PASSING_JOBS = (
    "strong_fixed_apply",
    "strong_hourly_apply",
    "thin_client_flagged",
    "sparse_no_metadata",
)
ALL_JOBS = HARD_REJECT_JOBS + GATE_PASSING_JOBS


def load_job(name: str) -> str:
    """Return a fixture posting's raw text, as a freelancer would paste it."""
    return (JOBS_DIR / f"{name}.txt").read_text()
