"""Validated API and domain models for the proposal workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RequestStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    FAILED = "failed"


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ClientRequestCreate(StrictModel):
    company_name: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=200)
    contact_email: EmailStr
    requirements: str = Field(min_length=20, max_length=10_000)


class ClientRequestRecord(ClientRequestCreate):
    request_id: UUID = Field(default_factory=uuid4)
    status: RequestStatus = RequestStatus.RECEIVED
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceItem(StrictModel):
    service_code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,49}$")
    service_name: str = Field(min_length=2, max_length=200)
    unit: str = Field(min_length=1, max_length=50)
    unit_price: Decimal = Field(gt=Decimal("0"), decimal_places=2)
    minimum_quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    active: bool = True
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("currency must contain letters only")
        return normalized


class ProposalLineItem(StrictModel):
    service_code: str
    description: str = Field(min_length=2, max_length=500)
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_price: Decimal = Field(ge=Decimal("0"), decimal_places=2)
    line_total: Decimal = Field(ge=Decimal("0"), decimal_places=2)


class SourceReference(StrictModel):
    document_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=1_000)


class ProposalRecord(StrictModel):
    proposal_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    line_items: list[ProposalLineItem] = Field(default_factory=list)
    subtotal: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    discount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    tax: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    total: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    sources: list[SourceReference] = Field(default_factory=list)
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None
    approval_comment: str | None = Field(default=None, max_length=2_000)


class HealthResponse(StrictModel):
    status: str
    service: str
    version: str
    environment: str
    database: str

