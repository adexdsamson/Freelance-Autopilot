"""The three Gig Triage tools (TRI-01, TRI-02, TRI-03).

Each is a `@tool`-decorated function, matching the shape Phase 1's spike
established (D-07): the decorator turns the type hints and docstring into the
schema a model sees, and the function stays directly callable from Python, so
the deterministic driver in `agents/gig_triage_agent.py` can call these in a
fixed order without going through a model.

This module must never import the store (REC-03/D-05, enforced by
`tests/test_single_writer.py`). It returns plain dicts; Strands auto-wraps
them, and the driver validates them back into the Pydantic models.

Division of labour, and why it matters: `extract_job_fields` and
`kill_switch_check` are pure functions of their input with no network call at
all. Only `llm_scorecard` reaches Bedrock. That boundary is what makes TRI-02
unit-testable without credentials, and it means a posting the gate rejects
costs zero tokens.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from strands import Agent, tool
from strands.models import BedrockModel

from models.triage import (
    ClientStats,
    ExtractedJobFields,
    KillSwitchResult,
    Scorecard,
    ScorecardJudgment,
)
from tools.triage_config import (
    HEALTHY_CLIENT_HIRE_RATE,
    HEALTHY_CLIENT_SPEND_USD,
    MIN_CLIENT_HIRE_RATE,
    MIN_CLIENT_SPEND_USD,
    MIN_FIXED_BUDGET_USD,
    MIN_HOURLY_RATE_USD,
    RED_FLAG_KEYWORDS,
    SCORE_WEIGHTS,
)

# D-06: model id and region stay explicit and env-driven, never a bare
# model-id string handed to Agent(model=...).
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# DEMO-02 needs three identical fixture runs. Temperature 0 is necessary for
# that but not sufficient (Bedrock does not promise bit-identical sampling),
# which is the other reason the composite score is computed in code.
SCORECARD_TEMPERATURE = 0.0


# ---------------------------------------------------------------------------
# TRI-01: extract_job_fields
# ---------------------------------------------------------------------------

# Marks the start of the client-history block in a pasted posting. Splitting
# on it is what stops "$120K total spent" (a client stat) from being read as
# the job's budget -- the budget scan only ever sees text above this line.
_CLIENT_SECTION_RE = re.compile(
    r"^\s*(?:about\s+(?:the\s+)?client|client\s+history|client\s+info(?:rmation)?|client)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_MONEY = r"\$\s*([\d,]+(?:\.\d+)?)\s*([kKmM])?"

_HOURLY_RE = re.compile(_MONEY + r"[^\n]{0,20}?(?:/|\bper\s+)\s*(?:hr|hour)\b", re.IGNORECASE)
_HOURLY_LABEL_RE = re.compile(r"hourly[^\n$]{0,30}" + _MONEY, re.IGNORECASE)
_BUDGET_LABEL_RE = re.compile(
    r"(?:est\.?\s*)?(?:budget|fixed[-\s]?price)[^\n$]{0,30}" + _MONEY, re.IGNORECASE
)
_ANY_MONEY_RE = re.compile(_MONEY)

_SPEND_RE = re.compile(_MONEY + r"\+?\s*(?:total\s+)?spen[dt]", re.IGNORECASE)
_SPEND_LABEL_RE = re.compile(r"total\s+spen[dt]\s*:?\s*" + _MONEY, re.IGNORECASE)
_HIRE_RATE_RE = re.compile(r"([\d.]+)\s*%\s*hire\s*rate", re.IGNORECASE)
_HIRE_RATE_LABEL_RE = re.compile(r"hire\s*rate\s*:?\s*([\d.]+)\s*%", re.IGNORECASE)
_HIRES_RE = re.compile(r"([\d,]+)\s*hires?\b", re.IGNORECASE)
_JOBS_POSTED_RE = re.compile(r"([\d,]+)\s*jobs?\s*posted", re.IGNORECASE)
_UNVERIFIED_RE = re.compile(r"payment\s*(?:method\s*)?(?:not\s+verified|unverified)", re.IGNORECASE)
_VERIFIED_RE = re.compile(r"payment\s*(?:method\s*)?verified", re.IGNORECASE)


def _money(amount: str, suffix: Optional[str]) -> float:
    """Turn a regex money capture into a float, expanding a K/M suffix."""
    value = float(amount.replace(",", ""))
    if suffix:
        value *= {"k": 1_000, "m": 1_000_000}[suffix.lower()]
    return value


def _split_client_section(raw_text: str) -> tuple[str, str]:
    """Return (job_text, client_text).

    When no client-history heading is present the client scan falls back to
    the whole posting, but the job scan does not lose anything by it: the
    budget patterns are anchored to budget wording, and the bare-dollar
    fallback explicitly skips amounts adjacent to "spent".
    """
    match = _CLIENT_SECTION_RE.search(raw_text)
    if not match:
        return raw_text, raw_text
    return raw_text[: match.start()], raw_text[match.start() :]


def _extract_budget(job_text: str) -> tuple[Optional[float], str]:
    """Return (amount, budget_type) for the job's stated pay.

    Ordered most-specific first. Hourly is checked before any fixed pattern
    because "Budget: $60/hr" matches both, and reading it as a $60 fixed
    project would hard-reject a perfectly good contract.
    """
    for pattern in (_HOURLY_RE, _HOURLY_LABEL_RE):
        if match := pattern.search(job_text):
            return _money(match.group(1), match.group(2)), "hourly"

    if match := _BUDGET_LABEL_RE.search(job_text):
        return _money(match.group(1), match.group(2)), "fixed"

    # Fallback: the first bare dollar amount that is not a client-spend
    # figure. Treated as fixed-price, which is the default posting type when
    # an amount is quoted without a rate unit.
    for match in _ANY_MONEY_RE.finditer(job_text):
        trailing = job_text[match.end() : match.end() + 20].lower()
        if "spen" in trailing:
            continue
        return _money(match.group(1), match.group(2)), "fixed"

    return None, "unknown"


def _extract_client_stats(client_text: str) -> ClientStats:
    """Parse the client-history block. Anything absent stays None."""
    total_spend: Optional[float] = None
    for pattern in (_SPEND_LABEL_RE, _SPEND_RE):
        if match := pattern.search(client_text):
            total_spend = _money(match.group(1), match.group(2))
            break

    hire_rate: Optional[float] = None
    for pattern in (_HIRE_RATE_RE, _HIRE_RATE_LABEL_RE):
        if match := pattern.search(client_text):
            # Stored 0.0-1.0; clamped because a posting claiming "120% hire
            # rate" must not blow up ClientStats' le=1.0 bound.
            hire_rate = min(float(match.group(1)) / 100.0, 1.0)
            break

    hires = int(m.group(1).replace(",", "")) if (m := _HIRES_RE.search(client_text)) else None
    jobs_posted = (
        int(m.group(1).replace(",", "")) if (m := _JOBS_POSTED_RE.search(client_text)) else None
    )

    # Order matters: "payment method not verified" contains "payment method
    # verified" as a substring only after the negation is ruled out first.
    if _UNVERIFIED_RE.search(client_text):
        payment_verified: Optional[bool] = False
    elif _VERIFIED_RE.search(client_text):
        payment_verified = True
    else:
        payment_verified = None

    return ClientStats(
        total_spend=total_spend,
        hire_rate=hire_rate,
        hires=hires,
        jobs_posted=jobs_posted,
        payment_verified=payment_verified,
    )


@tool
def extract_job_fields(raw_text: str) -> dict:
    """Extract structured fields from raw pasted job-posting text.

    Use this first, on the text a freelancer pasted out of a job board, to
    recover the title, description, budget and client history before any
    judgement is made about the gig.

    Args:
        raw_text: The full posting as pasted, including any client-history
            block.

    Returns:
        A dict matching ExtractedJobFields: title, description, budget,
        budget_type ("fixed" | "hourly" | "unknown") and client_stats.
    """
    stripped = raw_text.strip()
    if not stripped:
        raise ValueError("extract_job_fields received empty job text")

    job_text, client_text = _split_client_section(stripped)

    lines = [line.strip() for line in job_text.splitlines()]
    non_empty = [line for line in lines if line]
    title = non_empty[0] if non_empty else stripped.splitlines()[0].strip()

    # Description is the posting body minus the title line. Metadata lines
    # (budget, posting type) are left in on purpose -- they are context the
    # scorecard should see, and dropping them risks discarding real
    # requirements that happen to sit on a short line.
    body = "\n".join(non_empty[1:]).strip()
    description = body or title

    budget, budget_type = _extract_budget(job_text)

    return ExtractedJobFields(
        title=title,
        description=description,
        budget=budget,
        budget_type=budget_type,
        client_stats=_extract_client_stats(client_text),
    ).model_dump()


# ---------------------------------------------------------------------------
# TRI-02: kill_switch_check
# ---------------------------------------------------------------------------


@tool
def kill_switch_check(extracted_fields: dict) -> dict:
    """Apply the deterministic disqualification gate to an extracted job.

    Use this after extract_job_fields and before any scoring. It makes no
    model call: it applies fixed budget floors, a red-flag phrase list, and
    client spend/hire-rate thresholds from tools/triage_config.py.

    Args:
        extracted_fields: An ExtractedJobFields-shaped dict.

    Returns:
        A dict matching KillSwitchResult: passed, rejections (disqualifying),
        flags (non-fatal concerns for the scorecard to weigh).
    """
    fields = ExtractedJobFields.model_validate(extracted_fields)
    rejections: list[str] = []
    flags: list[str] = []

    # --- Budget floor ---
    if fields.budget is None:
        flags.append("budget is not stated in the posting")
    elif fields.budget_type == "hourly":
        if fields.budget < MIN_HOURLY_RATE_USD:
            rejections.append(
                f"hourly rate ${fields.budget:,.2f}/hr is below the "
                f"${MIN_HOURLY_RATE_USD:,.2f}/hr floor"
            )
    elif fields.budget < MIN_FIXED_BUDGET_USD:
        rejections.append(
            f"fixed budget ${fields.budget:,.2f} is below the "
            f"${MIN_FIXED_BUDGET_USD:,.2f} floor"
        )

    # --- Red-flag phrases ---
    haystack = f"{fields.title}\n{fields.description}".lower()
    rejections.extend(
        f"posting contains red-flag phrase {phrase!r}"
        for phrase in RED_FLAG_KEYWORDS
        if phrase in haystack
    )

    # --- Client history ---
    stats = fields.client_stats
    if stats.total_spend is None:
        flags.append("client total spend is not stated")
    elif stats.total_spend < MIN_CLIENT_SPEND_USD:
        rejections.append(
            f"client has spent only ${stats.total_spend:,.2f}, below the "
            f"${MIN_CLIENT_SPEND_USD:,.2f} floor"
        )
    elif stats.total_spend < HEALTHY_CLIENT_SPEND_USD:
        flags.append(
            f"client spend ${stats.total_spend:,.2f} is thin (below "
            f"${HEALTHY_CLIENT_SPEND_USD:,.2f})"
        )

    if stats.hire_rate is None:
        flags.append("client hire rate is not stated")
    elif stats.hire_rate < MIN_CLIENT_HIRE_RATE:
        rejections.append(
            f"client hire rate {stats.hire_rate:.0%} is below the "
            f"{MIN_CLIENT_HIRE_RATE:.0%} floor"
        )
    elif stats.hire_rate < HEALTHY_CLIENT_HIRE_RATE:
        flags.append(
            f"client hire rate {stats.hire_rate:.0%} is weak (below "
            f"{HEALTHY_CLIENT_HIRE_RATE:.0%})"
        )

    if stats.payment_verified is False:
        flags.append("client payment method is not verified")
    elif stats.payment_verified is None:
        flags.append("client payment-verification status is not stated")

    return KillSwitchResult(
        passed=not rejections, rejections=rejections, flags=flags
    ).model_dump()


# ---------------------------------------------------------------------------
# TRI-03: llm_scorecard
# ---------------------------------------------------------------------------

SCORECARD_SYSTEM_PROMPT = """\
You score freelance job postings for a specific freelancer deciding whether \
to spend a proposal credit. Score three dimensions from 0 to 10:

- fit_score: how well the work matches a senior software freelancer's \
delivery capability, and how clearly the requirements are specified.
- competition_score: how favourable the competitive position looks. HIGH \
means little competition or a specialised ask; LOW means a generic, \
commodity posting that hundreds will bid on.
- rate_reasonableness_score: whether the stated pay is reasonable for the \
scope described. HIGH means well-paid for the work; LOW means underpaid.

Be strict and consistent: the same posting must always receive the same \
scores. Weigh every concern listed under CONCERNS -- they were raised by a \
deterministic pre-screen and are real. Keep `reasoning` to two or three \
sentences naming the decisive factors."""


def _scorecard_prompt(fields: ExtractedJobFields, flags: list[str]) -> str:
    budget = (
        "not stated"
        if fields.budget is None
        else f"${fields.budget:,.2f} ({fields.budget_type})"
    )
    stats = fields.client_stats
    concerns = "\n".join(f"- {flag}" for flag in flags) or "- none"
    return (
        f"TITLE: {fields.title}\n\n"
        f"DESCRIPTION:\n{fields.description}\n\n"
        f"BUDGET: {budget}\n"
        f"CLIENT TOTAL SPEND: {stats.total_spend}\n"
        f"CLIENT HIRE RATE: {stats.hire_rate}\n"
        f"CLIENT PAYMENT VERIFIED: {stats.payment_verified}\n\n"
        f"CONCERNS:\n{concerns}"
    )


def _composite_score(judgment: ScorecardJudgment) -> float:
    """Blend the three sub-scores into a 0-100 composite.

    Computed here rather than asked of the model so identical sub-scores
    always yield an identical total (DEMO-02).
    """
    weighted = (
        judgment.fit_score * SCORE_WEIGHTS["fit"]
        + judgment.competition_score * SCORE_WEIGHTS["competition"]
        + judgment.rate_reasonableness_score * SCORE_WEIGHTS["rate"]
    )
    return round(weighted * 10.0, 2)


@tool
def llm_scorecard(extracted_fields: dict, flags: Optional[list[str]] = None) -> dict:
    """Score a job posting's fit, competition and rate reasonableness.

    Use this only on a posting that has already passed kill_switch_check.
    Runs a Bedrock-backed Claude judgement and returns sub-scores plus a
    code-computed composite.

    Args:
        extracted_fields: An ExtractedJobFields-shaped dict.
        flags: Non-fatal concerns from kill_switch_check, given to the model
            as context it must weigh.

    Returns:
        A dict matching Scorecard: fit_score, competition_score,
        rate_reasonableness_score, reasoning and the composite score (0-100).
    """
    fields = ExtractedJobFields.model_validate(extracted_fields)

    model = BedrockModel(
        model_id=MODEL_ID, region_name=REGION, temperature=SCORECARD_TEMPERATURE
    )
    judge = Agent(model=model, system_prompt=SCORECARD_SYSTEM_PROMPT)
    judgment = judge.structured_output(
        ScorecardJudgment, _scorecard_prompt(fields, flags or [])
    )

    return Scorecard(
        **judgment.model_dump(), score=_composite_score(judgment)
    ).model_dump()
