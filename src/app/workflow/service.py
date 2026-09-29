"""Business service for draft generation and controlled manager decisions."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import hmac
from pathlib import Path
import secrets
import shutil
from uuid import UUID, uuid4

from app.domain import ProposalStatus
from app.ingestion.security import IngestionLimits
from app.pricing.catalog import load_catalog
from app.pricing.engine import PricingEngine, VolumeDiscountRule
from app.proposals.generator import ProposalGenerator
from app.proposals.models import ProposalDocumentData
from app.workflow.errors import DraftUnavailableError, InvalidReviewTokenError
from app.workflow.models import CreateWorkflowRequest, DecisionResponse, ProposalStatusResponse
from app.workflow.repository import WorkflowRepository


class WorkflowService:
    def __init__(
        self,
        *,
        repository: WorkflowRepository,
        catalog_path: Path,
        output_dir: Path,
        vat_rate: Decimal,
        discount_threshold: Decimal,
        discount_rate: Decimal,
        generator: ProposalGenerator | None = None,
    ) -> None:
        self.repository = repository
        self.catalog_path = Path(catalog_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.vat_rate = vat_rate
        self.discount_threshold = discount_threshold
        self.discount_rate = discount_rate
        self.generator = generator or ProposalGenerator()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _verify_token(self, proposal_id: UUID, token: str):
        proposal = self.repository.get_proposal(proposal_id)
        stored_hash = proposal["review_token_hash"]
        if not stored_hash or not hmac.compare_digest(stored_hash, self._hash_token(token)):
            raise InvalidReviewTokenError("Review token is invalid")
        return proposal

    def create(self, payload: CreateWorkflowRequest) -> tuple[UUID, UUID, str]:
        request_id, proposal_id = uuid4(), uuid4()
        target = self.output_dir / str(proposal_id)
        try:
            catalog = load_catalog(
                self.catalog_path,
                allowed_root=self.catalog_path.parent,
                limits=IngestionLimits(),
            )
            pricing = PricingEngine(
                catalog,
                vat_rate=self.vat_rate,
                discount_rule=VolumeDiscountRule(self.discount_threshold, self.discount_rate),
            ).calculate(payload.requested_services)
            today = date.today()
            document_data = ProposalDocumentData(
                proposal_id=proposal_id,
                prepared_on=today,
                valid_until=today + timedelta(days=14),
                client_company=payload.company_name,
                client_contact=payload.contact_name,
                project_title=payload.project_title,
                executive_summary=payload.executive_summary,
                scope_items=payload.scope_items,
                evidence=payload.evidence,
                pricing=pricing,
            )
            docx_path = target / "proposal-draft.docx"
            pdf_path = target / "proposal-draft.pdf"
            self.generator.generate(document_data, docx_path, pdf_path)
            token = secrets.token_urlsafe(32)
            self.repository.create_pending(
                request_id=request_id,
                proposal_id=proposal_id,
                company_name=payload.company_name,
                contact_name=payload.contact_name,
                contact_email=str(payload.contact_email),
                requirements=payload.requirements,
                currency=pricing.currency,
                total=str(pricing.total),
                docx_path=docx_path,
                pdf_path=pdf_path,
                review_token_hash=self._hash_token(token),
            )
            return request_id, proposal_id, token
        except Exception as exc:
            # A failed conversion may leave a valid-looking DOCX or partial PDF.
            # Remove the proposal-specific directory before recording failure so
            # no stale artifact can later be mistaken for an approved output.
            shutil.rmtree(target, ignore_errors=True)
            error_code = getattr(exc, "code", exc.__class__.__name__.lower())
            self.repository.record_failure(
                request_id=request_id,
                proposal_id=proposal_id,
                company_name=payload.company_name,
                contact_name=payload.contact_name,
                contact_email=str(payload.contact_email),
                requirements=payload.requirements,
                error_code=str(error_code),
                error_message=str(exc)[:1000],
            )
            raise

    def status(self, proposal_id: UUID) -> ProposalStatusResponse:
        row = self.repository.get_proposal(proposal_id)
        return ProposalStatusResponse(
            proposal_id=UUID(row["proposal_id"]),
            request_id=UUID(row["request_id"]),
            status=ProposalStatus(row["status"]),
            currency=row["currency"],
            total=Decimal(row["total"]) if row["total"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            decided_at=datetime.fromisoformat(row["decided_at"]) if row["decided_at"] else None,
            can_finalize=row["status"] == ProposalStatus.APPROVED,
            error_code=row["error_code"],
            error_message=row["error_message"],
        )

    def draft_path(self, proposal_id: UUID, token: str, kind: str) -> Path:
        row = self._verify_token(proposal_id, token)
        path = Path(row[f"{kind}_path"]) if row[f"{kind}_path"] else None
        if path is None or not path.is_file():
            raise DraftUnavailableError("Draft file is unavailable")
        return path

    def decide(
        self,
        *,
        proposal_id: UUID,
        action: str,
        token: str,
        manager_name: str,
        comment: str | None,
        idempotency_key: str,
    ) -> DecisionResponse:
        self._verify_token(proposal_id, token)
        row, replay, decision = self.repository.decide(
            proposal_id=proposal_id,
            action=action,
            manager_name=manager_name,
            comment=comment,
            idempotency_key=idempotency_key,
        )
        status = ProposalStatus(row["status"])
        return DecisionResponse(
            proposal_id=proposal_id,
            status=status,
            decision=action,
            manager_name=decision["manager_name"],
            comment=decision["comment"],
            decided_at=datetime.fromisoformat(row["decided_at"]),
            idempotent_replay=replay,
            can_finalize=status == ProposalStatus.APPROVED,
            message="Decision already recorded" if replay else "Manager decision recorded",
        )
