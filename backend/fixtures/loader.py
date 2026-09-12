"""D-04/DEMO-01: pure-data fixture loader for the ops stage.

Loads the client-thread and payment-schedule fixtures (creep/clean
variants) plus the Upwork jobs fixture. Pure `json.loads` over a bundled
file — no store import, no network, no side effects.

This module must NOT import the store (single-writer guard, REC-03/D-05 —
backend/tests/test_single_writer.py scans backend/tools/ for store
imports; this file lives alongside backend/tools/ in spirit and follows
the same rule even though backend/fixtures/ is not itself scanned).
"""
from __future__ import annotations

import json
from pathlib import Path

_FIXTURES_DIR = Path(__file__).parent

# D-04: "creep" is the default/base filename, "clean" is the sibling
# variant suffixed "_clean" — e.g. sample_client_thread.json (creep) vs
# sample_client_thread_clean.json (clean).
_VARIANT_SUFFIX = {"creep": "", "clean": "_clean"}


def load_client_thread(variant: str = "creep") -> list[str]:
    """Load the client-thread fixture for the given variant ("creep" or
    "clean"). Returns a list of message strings."""
    if variant not in _VARIANT_SUFFIX:
        raise ValueError(f"unknown fixture variant {variant!r}; expected 'creep' or 'clean'")
    suffix = _VARIANT_SUFFIX[variant]
    path = _FIXTURES_DIR / f"sample_client_thread{suffix}.json"
    return json.loads(path.read_text())


def load_payment_schedule(variant: str = "creep") -> list[dict]:
    """Load the payment-schedule fixture for the given variant ("creep" or
    "clean"). Returns a list of {"label", "amount", "due_date", "paid"}
    dicts."""
    if variant not in _VARIANT_SUFFIX:
        raise ValueError(f"unknown fixture variant {variant!r}; expected 'creep' or 'clean'")
    suffix = _VARIANT_SUFFIX[variant]
    path = _FIXTURES_DIR / f"sample_payment_schedule{suffix}.json"
    return json.loads(path.read_text())


def load_upwork_jobs() -> list[dict]:
    """Load the Upwork jobs fixture (DEMO-01). Returns a list of mixed-fit
    job posting dicts."""
    path = _FIXTURES_DIR / "sample_upwork_jobs.json"
    return json.loads(path.read_text())
