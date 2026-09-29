from datetime import date
from uuid import UUID

from pydantic import Field

from app.domain import StrictModel
from app.pricing.models import PricingResult


class EvidenceFact(StrictModel):
    statement: str = Field(min_length=5, max_length=1000)
    source_id: str = Field(min_length=5, max_length=100)
    source_location: str = Field(min_length=1, max_length=300)


class ProposalDocumentData(StrictModel):
    proposal_id: UUID
    prepared_on: date
    valid_until: date
    client_company: str = Field(min_length=2, max_length=200)
    client_contact: str = Field(min_length=2, max_length=200)
    project_title: str = Field(min_length=5, max_length=200)
    executive_summary: str = Field(min_length=30, max_length=3000)
    scope_items: list[str] = Field(min_length=1, max_length=20)
    evidence: list[EvidenceFact] = Field(min_length=1, max_length=30)
    pricing: PricingResult

