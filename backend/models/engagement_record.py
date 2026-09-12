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

from pydantic import BaseModel, Field


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


class ContractSlice(BaseModel):
    text: Optional[str] = None
    payment_schedule: list[dict] = Field(default_factory=list)


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
