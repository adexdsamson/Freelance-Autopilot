"""Engagement Record schema (Pydantic v2), mirroring PRD §6.2 exactly.

Every stage slice past `job` is Optional[...] = None (D-03) so a
freshly-captured record (job only) validates immediately, before triage,
proposal, contract, or ops has run. `engagement_id` is a server-generated
UUID (D-04) — never a raw string — which also closes off path-traversal
against FileEngagementStore._path() (T-01-01): a UUID cannot contain
path-separator or traversal characters.
"""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class JobSlice(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    client_stats: Optional[dict] = None


class TriageSlice(BaseModel):
    verdict: Literal["apply", "skip"]
    score: float
    reasoning: str


class ProposalSlice(BaseModel):
    text: Optional[str] = None
    needs_human_input: bool = False
    question: Optional[str] = None


class PaymentMilestone(BaseModel):
    label: str
    amount: float
    due_marker: str  # freeform symbolic marker, e.g. "on_signing" / "on_delivery" /
    # "net_15" — NOT a calendar date (no signing date exists yet at draft time).


class ContractSlice(BaseModel):
    text: Optional[str] = None
    payment_schedule: list[PaymentMilestone] = Field(default_factory=list)


class ProposalContractResult(BaseModel):
    """D-01: the Proposal-Contract specialist's ONE strict typed result.

    Two mutually-exclusive outcomes (SC3): either the happy path (populated
    proposal_text + contract_text + a non-empty payment_schedule) OR the
    escalation path (needs_human_input=True + a specific question, with no
    populated happy-path field). `needs_human_input`/`question` are
    first-class optional fields from the start so the ambiguous fixture
    escalates cleanly and never raises a structured-output exception (SC2).

    This validator is a runtime assertion on BOTH the deterministic path
    (construct this model, never a bare dict — Pitfall C) and the live
    Bedrock path (a validator ValueError becomes a tool-error ToolResult fed
    back to the model for a retry, never a raw Python exception — verified
    against installed strands-agents==1.54.0 source).
    """

    needs_human_input: bool = False
    question: Optional[str] = None
    proposal_text: Optional[str] = None
    contract_text: Optional[str] = None
    payment_schedule: list[PaymentMilestone] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_mutual_exclusivity(self) -> "ProposalContractResult":
        happy_fields_populated = bool(
            self.proposal_text or self.contract_text or self.payment_schedule
        )
        if self.needs_human_input:
            if happy_fields_populated:
                raise ValueError(
                    "needs_human_input=True must not carry a populated "
                    "proposal_text, contract_text, or payment_schedule (SC3)"
                )
            if not self.question:
                raise ValueError(
                    "needs_human_input=True requires a non-empty question"
                )
        else:
            if not (self.proposal_text and self.contract_text and self.payment_schedule):
                raise ValueError(
                    "the happy path requires proposal_text, contract_text, and "
                    "a non-empty payment_schedule"
                )
        return self


class OpsSlice(BaseModel):
    status_updates: list[dict] = Field(default_factory=list)
    scope_creep_flags: list[dict] = Field(default_factory=list)
    invoice_flags: list[dict] = Field(default_factory=list)


class EngagementRecord(BaseModel):
    engagement_id: UUID = Field(default_factory=uuid4)
    job: JobSlice
    triage: Optional[TriageSlice] = None
    proposal: Optional[ProposalSlice] = None
    contract: Optional[ContractSlice] = None
    ops: Optional[OpsSlice] = None
