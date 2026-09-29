from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain import ClientRequestCreate, ServiceItem


def test_client_request_rejects_short_requirements() -> None:
    with pytest.raises(ValidationError):
        ClientRequestCreate(
            company_name="Example Company",
            contact_name="Alex Morgan",
            contact_email="alex@example.com",
            requirements="Too short",
        )


def test_service_item_normalizes_currency() -> None:
    item = ServiceItem(
        service_code="AUTO_SETUP",
        service_name="Automation setup",
        unit="project",
        unit_price=Decimal("750.00"),
        currency="eur",
    )

    assert item.currency == "EUR"

