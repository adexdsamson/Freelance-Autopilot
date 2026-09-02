"""FastAPI app — the sole Engagement Record writer (REC-03/D-05).

POST /capture: validate a structured job payload, run triage via the
TriageRunner DI seam, merge the typed TriageSlice VERBATIM (no
re-authoring — D-02/ORC-02), persist, and return the verdict.

GET /engagements/{engagement_id}: read-through the store; 404 for an
unknown id. `engagement_id` is typed UUID at the path param, which closes
path traversal structurally (T-03-03) — FileEngagementStore._path()
independently raises TypeError on any non-UUID.

api.py is the ONLY module in this codebase that imports the store.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from agents.triage_runner import TriageRunner, get_triage_runner
from models.engagement_record import EngagementRecord, JobSlice
from store.engagement_store import EngagementStore
from store.file_engagement_store import FileEngagementStore

app = FastAPI()
_store = FileEngagementStore()  # single construction point (Phase 1's swap seam)


def get_store() -> EngagementStore:
    return _store


class CaptureResponse(BaseModel):
    engagement_id: UUID
    verdict: str
    score: float
    reasoning: str


@app.post("/capture", response_model=CaptureResponse)
def capture(
    job: JobSlice,
    store: Annotated[EngagementStore, Depends(get_store)],
    triage_runner: Annotated[TriageRunner, Depends(get_triage_runner)],
) -> CaptureResponse:
    record = EngagementRecord(job=job)
    record.triage = triage_runner(job)  # typed, VERBATIM merge (D-02/ORC-02)
    store.create(record)
    return CaptureResponse(
        engagement_id=record.engagement_id,
        verdict=record.triage.verdict,
        score=record.triage.score,
        reasoning=record.triage.reasoning,
    )


@app.get("/engagements/{engagement_id}", response_model=EngagementRecord)
def get_engagement(
    engagement_id: UUID,
    store: Annotated[EngagementStore, Depends(get_store)],
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return record
