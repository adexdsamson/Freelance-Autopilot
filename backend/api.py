"""FastAPI app — the sole Engagement Record writer (REC-03/D-05).

POST /capture: validate a structured job payload, run triage via the
TriageRunner DI seam, merge the typed TriageSlice VERBATIM (no
re-authoring — D-02/ORC-02), persist, and return the verdict.

GET /engagements/{engagement_id}: read-through the store; 404 for an
unknown id. `engagement_id` is typed UUID at the path param, which closes
path traversal structurally (T-03-03) — FileEngagementStore._path()
independently raises TypeError on any non-UUID.

POST /engagements/{engagement_id}/advance?stage=proposal: load the record
(404 if unknown), guard that triage exists and verdict == "apply" (409
otherwise), run the Proposal-Contract specialist via the ProposalRunner DI
seam, merge the typed ProposalContractResult VERBATIM into proposal (+
contract on the happy path only, explicitly cleared to None on escalation
so a re-advance can never leave a stale contract alongside
needs_human_input=True (CR-01/SC3) — no re-authoring, D-02/D-05), persist
via store.save, and return the updated record. An unsupported `stage`
value is a 400 (T-05-03) — Phase 6 adds `stage="ops"` here without a
rewrite.

api.py is the ONLY module in this codebase that imports the store.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from strands.types.exceptions import (
    ContextWindowOverflowException,
    ModelThrottledException,
)

from agents.proposal_runner import ProposalRunner, get_proposal_runner
from agents.triage_runner import TriageRunner, get_triage_runner
from models.engagement_record import (
    ContractSlice,
    EngagementRecord,
    JobSlice,
    ProposalContractResult,
    ProposalSlice,
)
from store.engagement_store import EngagementStore
from store.file_engagement_store import FileEngagementStore

app = FastAPI()
_store: EngagementStore | None = None


def get_store() -> EngagementStore:
    # Lazy single construction point (Phase 1's swap seam). Constructing at
    # first-use rather than import time avoids a cwd-relative mkdir side effect
    # when the module is merely imported (e.g. by tests or tooling).
    global _store
    if _store is None:
        _store = FileEngagementStore()
    return _store


class CaptureResponse(BaseModel):
    engagement_id: UUID
    verdict: str
    score: float
    reasoning: str


class BedrockUnavailableError(RuntimeError):
    """Readable, non-leaking Bedrock failure (T-03-02).

    Never includes the raw AWS error `Message` or any credential literal —
    only the exception type / `Error.Code`. Reuses Phase 1's proven
    taxonomy (backend/scripts/smoke_test_bedrock_connectivity.py).
    """


def map_bedrock_error(exc: Exception) -> BedrockUnavailableError:
    """Map a botocore/Bedrock exception to a static, credential-free message.

    Mirrors backend/scripts/smoke_test_bedrock_connectivity.py's taxonomy:
    NoCredentialsError -> static string; ClientError -> Error.Code only
    (never Message); strands ModelThrottledException / ContextWindowOverflowException
    (plain Exception subclasses, NOT BotoCoreError — so they must be handled
    before the BotoCoreError branch and are caught by /capture's catch-all);
    BotoCoreError -> exception type name only; anything else -> exception type
    name only.
    """
    if isinstance(exc, NoCredentialsError):
        return BedrockUnavailableError("no AWS credentials found for Bedrock.")
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        return BedrockUnavailableError(
            f"Bedrock ClientError [{code}] — see the Bedrock console."
        )
    if isinstance(exc, ModelThrottledException):
        return BedrockUnavailableError(
            "Bedrock throttled the triage model invocation; retry with backoff."
        )
    if isinstance(exc, ContextWindowOverflowException):
        return BedrockUnavailableError(
            "the triage prompt exceeded the model's context window."
        )
    if isinstance(exc, BotoCoreError):
        return BedrockUnavailableError(
            f"AWS SDK error ({type(exc).__name__}) talking to Bedrock."
        )
    return BedrockUnavailableError(
        f"unexpected error contacting Bedrock ({type(exc).__name__})."
    )


@app.post("/capture", response_model=CaptureResponse)
def capture(
    job: JobSlice,
    store: Annotated[EngagementStore, Depends(get_store)],
    triage_runner: Annotated[TriageRunner, Depends(get_triage_runner)],
) -> CaptureResponse:
    record = EngagementRecord(job=job)
    try:
        record.triage = triage_runner(job)  # typed, VERBATIM merge (D-02/ORC-02)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — /capture must never surface a raw 500 from triage
        # Any triage failure (botocore creds/ClientError/timeout, strands
        # ModelThrottled/ContextWindowOverflow, or an unexpected type) maps to a
        # readable, credential-free 503. map_bedrock_error emits only the
        # exception type / Error.Code — never the raw AWS Message or a secret.
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped
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


@app.post("/engagements/{engagement_id}/advance", response_model=EngagementRecord)
def advance(
    engagement_id: UUID,
    stage: str,
    store: Annotated[EngagementStore, Depends(get_store)],
    proposal_runner: Annotated[ProposalRunner, Depends(get_proposal_runner)],
) -> EngagementRecord:
    record = store.get(engagement_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Engagement not found")

    if stage != "proposal":
        # Phase 6 adds an `elif stage == "ops":` branch here without
        # rewriting the guard/merge shape above or below this line (D-05).
        raise HTTPException(status_code=400, detail=f"unsupported stage '{stage}'")

    if record.triage is None or record.triage.verdict != "apply":
        raise HTTPException(
            status_code=409,
            detail="engagement is not apply-triaged; cannot draft a proposal",
        )

    try:
        result: ProposalContractResult = proposal_runner(record.job)  # typed, VERBATIM merge (D-02/D-05)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — /advance must never surface a raw 500
        # Any proposal-drafting failure (botocore creds/ClientError/timeout,
        # strands ModelThrottled/ContextWindowOverflow, or an unexpected
        # type) maps to a readable, credential-free 503 — the deterministic
        # default path never touches Bedrock so this only activates when
        # PROPOSAL_BACKEND=supervisor.
        mapped = map_bedrock_error(exc)
        raise HTTPException(status_code=503, detail=str(mapped)) from mapped

    record.proposal = ProposalSlice(
        text=result.proposal_text,
        needs_human_input=result.needs_human_input,
        question=result.question,
    )
    if result.needs_human_input:
        # CR-01: an escalation result must clear any stale contract from a
        # prior /advance call on this same engagement -- otherwise the
        # persisted record (and this response) could carry
        # needs_human_input=True alongside a fully populated contract,
        # violating SC3 at the persisted-record level (the schema-level
        # validator only enforces exclusivity within a SINGLE result, not
        # across repeated /advance calls).
        record.contract = None
    else:
        record.contract = ContractSlice(
            text=result.contract_text,
            payment_schedule=result.payment_schedule,
        )
    store.save(record)
    return record
