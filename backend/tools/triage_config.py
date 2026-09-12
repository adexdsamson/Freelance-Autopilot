"""Deterministic triage policy knobs (TRI-02).

Every threshold the kill switch enforces lives here rather than inline in
`triage_tools.py`, so a reviewer (or a judge watching the demo) can read the
entire policy in one screen without reading the algorithm, and so tuning the
demo never means editing gate logic.

These are *policy*, not tuning constants for an LLM: nothing in this module is
ever sent to a model. The gate that consumes them (`kill_switch_check`) makes
no network call, which is what lets TRI-02 be verified by a unit test with no
Bedrock credentials.
"""

# --- Budget floors -------------------------------------------------------
# A posting below either floor is a hard reject: no LLM opinion is worth the
# token spend on a job the freelancer has already decided is under-priced.
MIN_FIXED_BUDGET_USD = 500.0
MIN_HOURLY_RATE_USD = 35.0

# --- Client-history floors -----------------------------------------------
# Two-tier ladder. Below the MIN_*, the client is a hard reject. Between the
# MIN_* and the HEALTHY_*, the client is merely thin — that becomes a flag
# passed into the scorecard as context, so the LLM weighs it instead of the
# gate silently killing a viable gig.
MIN_CLIENT_SPEND_USD = 500.0
MIN_CLIENT_HIRE_RATE = 0.20
HEALTHY_CLIENT_SPEND_USD = 5_000.0
HEALTHY_CLIENT_HIRE_RATE = 0.50

# --- Verdict threshold ---------------------------------------------------
# Composite score (0-100) at or above which the verdict is "apply".
APPLY_SCORE_THRESHOLD = 60.0

# --- Composite score weights (must sum to 1.0) ---------------------------
# Fit dominates: a perfect rate on work the freelancer cannot do well is
# still a bad gig. Enforced by test_scorecard_weights_sum_to_one.
SCORE_WEIGHTS = {"fit": 0.50, "competition": 0.25, "rate": 0.25}

# --- Red-flag phrases ----------------------------------------------------
# Matched as lowercase *substrings* against title + description. These are
# multi-word phrases on purpose: single words ("equity", "test", "sample")
# false-positive constantly in legitimate postings, so every entry here is
# long enough that an innocent posting is unlikely to contain it verbatim.
# Each one denotes either unpaid labour or an off-platform payment scam --
# both of which no score should be able to override, hence hard reject.
RED_FLAG_KEYWORDS = (
    "unpaid test",
    "unpaid trial",
    "unpaid sample",
    "spec work",
    "equity only",
    "equity instead of payment",
    "revenue share only",
    "profit share instead of payment",
    "pay outside upwork",
    "pay outside of upwork",
    "off-platform payment",
    "contact me on telegram",
    "contact me on whatsapp",
    "send your paypal",
    "wire transfer upfront",
)
