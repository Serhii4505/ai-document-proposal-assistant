from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from app.domain import ServiceItem
from app.pricing.catalog import ServiceCatalog
from app.pricing.engine import PricingEngine, VolumeDiscountRule
from app.pricing.models import RequestedService
from app.proposals import EvidenceFact, ProposalDocumentData, ProposalGenerator


output = Path("output/demo")
catalog = ServiceCatalog(items={
    "AUTO_SETUP": ServiceItem(service_code="AUTO_SETUP", service_name="Customer Request Automation", unit="project", unit_price=Decimal("1500.00"), minimum_quantity=1, active=True, currency="EUR"),
    "TRAINING": ServiceItem(service_code="TRAINING", service_name="Staff Training", unit="session", unit_price=Decimal("250.00"), minimum_quantity=1, active=True, currency="EUR"),
}, currency="EUR")
pricing = PricingEngine(catalog, vat_rate=Decimal("0.23"), discount_rule=VolumeDiscountRule()).calculate([
    RequestedService(service_code="AUTO_SETUP", quantity=2),
    RequestedService(service_code="TRAINING", quantity=2),
])
data = ProposalDocumentData(
    proposal_id=UUID("d02b3fee-4d0a-4b9f-9c34-9be9d1c54001"),
    prepared_on=date(2026, 9, 28), valid_until=date(2026, 10, 12),
    client_company="Example Manufacturing Ltd", client_contact="Alex Morgan",
    project_title="Customer Request Automation Implementation",
    executive_summary="Northstar Automation proposes a controlled customer request workflow with structured intake, validation, Google Sheets storage, internal email notifications and staff training.",
    scope_items=["Configure customer request intake and validation.", "Connect approved Google Sheets and internal email notification steps.", "Provide two staff training sessions."],
    evidence=[
        EvidenceFact(statement="Customer request automation includes email notifications and Google Sheets integration.", source_id="catalogue-page-1", source_location="catalogue.pdf - page 1"),
        EvidenceFact(statement="Staff training is available as an optional service.", source_id="terms-paragraph-4", source_location="terms.docx - paragraph 4"),
    ], pricing=pricing,
)
ProposalGenerator().generate(data, output / "northstar-commercial-proposal.docx", output / "northstar-commercial-proposal.pdf")
print(output.resolve())
