"""FastAPI routes called by n8n and the manager review interface."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.pricing.errors import PricingError
from app.proposals.errors import ProposalGenerationError
from app.workflow.errors import (
    DecisionConflictError,
    DraftUnavailableError,
    IdempotencyConflictError,
    InvalidReviewTokenError,
    ProposalNotFoundError,
)
from app.workflow.models import (
    AuditEventResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    DecisionResponse,
    ManagerDecisionRequest,
    ProposalStatusResponse,
    RejectDecisionRequest,
)
from app.workflow.service import WorkflowService


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProposalNotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, InvalidReviewTokenError):
        code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, (DecisionConflictError, IdempotencyConflictError)):
        code = status.HTTP_409_CONFLICT
    elif isinstance(exc, DraftUnavailableError):
        code = status.HTTP_410_GONE
    else:
        code = 422
    return HTTPException(status_code=code, detail={"code": getattr(exc, "code", "generation_failed"), "message": str(exc)})


def build_workflow_router(service: WorkflowService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["proposal workflow"])

    @router.post("/requests", response_model=CreateWorkflowResponse, status_code=status.HTTP_201_CREATED)
    def create_request(payload: CreateWorkflowRequest) -> CreateWorkflowResponse:
        try:
            request_id, proposal_id, token = service.create(payload)
        except (PricingError, ProposalGenerationError, ValueError, OSError) as exc:
            raise _http_error(exc) from exc
        return CreateWorkflowResponse(
            request_id=request_id,
            proposal_id=proposal_id,
            status="pending_approval",
            review_token=token,
            draft_docx_url=f"/api/v1/proposals/{proposal_id}/draft.docx?review_token={token}",
            draft_pdf_url=f"/api/v1/proposals/{proposal_id}/draft.pdf?review_token={token}",
            message="Draft created and waiting for manager approval",
        )

    @router.get("/proposals/{proposal_id}", response_model=ProposalStatusResponse)
    def proposal_status(proposal_id: UUID) -> ProposalStatusResponse:
        try:
            return service.status(proposal_id)
        except ProposalNotFoundError as exc:
            raise _http_error(exc) from exc

    @router.get("/proposals/{proposal_id}/draft.{kind}")
    def download_draft(
        proposal_id: UUID,
        kind: str,
        review_token: str = Query(min_length=20, max_length=200),
    ) -> FileResponse:
        if kind not in {"docx", "pdf"}:
            raise HTTPException(status_code=404, detail={"code": "unsupported_draft_format", "message": "Draft format is unsupported"})
        try:
            path = service.draft_path(proposal_id, review_token, kind)
        except (ProposalNotFoundError, InvalidReviewTokenError, DraftUnavailableError) as exc:
            raise _http_error(exc) from exc
        media_type = "application/pdf" if kind == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return FileResponse(path, media_type=media_type, filename=path.name)

    @router.post("/proposals/{proposal_id}/approve", response_model=DecisionResponse)
    def approve(proposal_id: UUID, payload: ManagerDecisionRequest) -> DecisionResponse:
        try:
            return service.decide(
                proposal_id=proposal_id,
                action="approve",
                token=payload.review_token,
                manager_name=payload.manager_name,
                comment=payload.comment,
                idempotency_key=payload.idempotency_key,
            )
        except (ProposalNotFoundError, InvalidReviewTokenError, DecisionConflictError, IdempotencyConflictError) as exc:
            raise _http_error(exc) from exc

    @router.post("/proposals/{proposal_id}/reject", response_model=DecisionResponse)
    def reject(proposal_id: UUID, payload: RejectDecisionRequest) -> DecisionResponse:
        try:
            return service.decide(
                proposal_id=proposal_id,
                action="reject",
                token=payload.review_token,
                manager_name=payload.manager_name,
                comment=payload.comment,
                idempotency_key=payload.idempotency_key,
            )
        except (ProposalNotFoundError, InvalidReviewTokenError, DecisionConflictError, IdempotencyConflictError) as exc:
            raise _http_error(exc) from exc

    @router.get("/proposals/{proposal_id}/events", response_model=list[AuditEventResponse])
    def events(
        proposal_id: UUID,
        review_token: str = Query(min_length=20, max_length=200),
    ) -> list[AuditEventResponse]:
        try:
            service._verify_token(proposal_id, review_token)
            rows = service.repository.get_events(proposal_id)
        except (ProposalNotFoundError, InvalidReviewTokenError) as exc:
            raise _http_error(exc) from exc
        return [
            AuditEventResponse(
                event_id=row["event_id"], entity_type=row["entity_type"], entity_id=row["entity_id"],
                event_type=row["event_type"], status=row["status"], details=json.loads(row["details_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    return router
