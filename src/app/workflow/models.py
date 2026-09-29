"""Validated Phase 6 request, response and audit models."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.domain import ProposalStatus, StrictModel
from app.pricing.models import RequestedService
from app.proposals.models import EvidenceFact


class CreateWorkflowRequest(StrictModel):
    company_name: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=200)
    contact_email: EmailStr
    requirements: str = Field(min_length=20, max_length=10_000)
    project_title: str = Field(min_length=5, max_length=200)
    executive_summary: str = Field(min_length=30, max_length=3_000)
    scope_items: list[str] = Field(min_length=1, max_length=20)
    evidence: list[EvidenceFact] = Field(min_length=1, max_length=30)
    requested_services: list[RequestedService] = Field(min_length=1, max_length=30)


class CreateWorkflowResponse(StrictModel):
    request_id: UUID
    proposal_id: UUID
    status: ProposalStatus
    review_token: str
    draft_docx_url: str
    draft_pdf_url: str
    message: str


class ManagerDecisionRequest(StrictModel):
    review_token: str = Field(min_length=20, max_length=200)
    manager_name: str = Field(min_length=2, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=200, pattern=r"^[A-Za-z0-9._:-]+$")
    comment: str | None = Field(default=None, max_length=2_000)


class RejectDecisionRequest(ManagerDecisionRequest):
    comment: str = Field(min_length=3, max_length=2_000)


class DecisionResponse(StrictModel):
    proposal_id: UUID
    status: ProposalStatus
    decision: Literal["approve", "reject"]
    manager_name: str
    comment: str | None
    decided_at: datetime
    idempotent_replay: bool
    can_finalize: bool
    message: str


class ProposalStatusResponse(StrictModel):
    proposal_id: UUID
    request_id: UUID
    status: ProposalStatus
    currency: str | None
    total: Decimal | None
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None
    can_finalize: bool
    client_delivery_enabled: bool = False
    error_code: str | None
    error_message: str | None


class AuditEventResponse(StrictModel):
    event_id: int
    entity_type: str
    entity_id: str
    event_type: str
    status: str
    details: dict[str, object]
    created_at: datetime
