"""Stage 1 (Gig Triage) schemas — TRI-01 through TRI-04.

These sit alongside `engagement_record.py` rather than inside it because they
are the *specialist's* contract, not the record's: Phase 3's FastAPI layer is
what merges a `TriageResult` into `EngagementRecord.triage` (REC-03/D-05 — an
agent never writes the record itself). `ExtractedJobFields` is deliberately
field-compatible with `JobSlice` (title / description / budget /
client_stats), so that merge is a copy rather than a translation.

`extra="forbid"` is set on the contract models but NOT on the one model an
LLM fills (`ScorecardJudgment`) — see its docstring for why the asymmetry is
deliberate.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClientStats(BaseModel):
    """Client-history signals parsed off a pasted posting (TRI-01).

    Every field is Optional because real pastes routinely omit some of them.
    Missing is NOT the same as zero and must never read as "fine": the gate
    flags an absent hire rate rather than treating it as a passing one.
    """

    model_config = ConfigDict(extra="forbid")

    total_spend: Optional[float] = None  # USD, client's lifetime spend
    hire_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hires: Optional[int] = Field(default=None, ge=0)
    jobs_posted: Optional[int] = Field(default=None, ge=0)
    payment_verified: Optional[bool] = None


class ExtractedJobFields(BaseModel):
    """Structured fields recovered from raw pasted job text (TRI-01).

    `budget_type` has no counterpart in PRD §6.2's `JobSlice`, and that is
    intentional: $65 fixed and $65/hr are wildly different propositions, so
    the gate cannot apply a budget floor without knowing which one it has.
    The field stays on the triage side of the boundary.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    budget: Optional[float] = Field(default=None, ge=0.0)
    budget_type: Literal["fixed", "hourly", "unknown"] = "unknown"
    client_stats: ClientStats = Field(default_factory=ClientStats)


class KillSwitchResult(BaseModel):
    """Outcome of the deterministic gate (TRI-02). Never involves an LLM.

    `rejections` are disqualifying and short-circuit triage to a "skip"
    verdict with no model call at all. `flags` are non-fatal concerns handed
    to the scorecard as context so the LLM weighs them explicitly instead of
    the gate quietly killing a viable gig.
    """

    model_config = ConfigDict(extra="forbid")

    passed: bool
    rejections: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class ScorecardJudgment(BaseModel):
    """The LLM's structured output for TRI-03 — sub-scores and reasoning only.

    Two deliberate omissions:

    1. No composite `score`. It is computed in code (see `Scorecard`) so the
       same three sub-scores always produce the same overall number. Letting
       the model also pick the total would add a second, unreproducible
       source of variance to a project whose DEMO-02 requirement is three
       byte-identical fixture runs.
    2. No `extra="forbid"`. This is the one model an LLM populates; a
       provider that returns a stray key should not crash a recorded demo,
       whereas the ge/le bounds below still reject genuinely bad numbers.
       The contract models the rest of the system reads DO forbid extras.
    """

    fit_score: float = Field(ge=0.0, le=10.0)
    competition_score: float = Field(ge=0.0, le=10.0)
    rate_reasonableness_score: float = Field(ge=0.0, le=10.0)
    reasoning: str


class Scorecard(ScorecardJudgment):
    """A `ScorecardJudgment` plus the code-computed composite (0-100)."""

    score: float = Field(ge=0.0, le=100.0)


class TriageResult(BaseModel):
    """The Gig Triage Agent's complete output (TRI-04).

    Exactly four fields, and `extra="forbid"` makes that structural rather
    than conventional: Stage 1 is fully autonomous, so there is no
    `needs_human_input` / `question` pair anywhere in this schema and no way
    to smuggle one in. That is the difference between Stage 1 and Stage 2's
    `ProposalSlice`, which escalates by design.
    """

    model_config = ConfigDict(extra="forbid")

    verdict: Literal["apply", "skip"]
    score: float = Field(ge=0.0, le=100.0)
    reasoning: str
    extracted_fields: ExtractedJobFields
