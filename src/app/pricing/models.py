"""Validated pricing input and output records."""

from decimal import Decimal

from pydantic import Field, field_validator

from app.domain import StrictModel


class RequestedService(StrictModel):
    service_code: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{1,49}$")
    quantity: Decimal = Field(gt=Decimal("0"))

    @field_validator("service_code", mode="before")
    @classmethod
    def normalize_service_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class PricedLine(StrictModel):
    service_code: str
    service_name: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class PricingResult(StrictModel):
    currency: str
    line_items: list[PricedLine] = Field(min_length=1)
    subtotal: Decimal
    discount_rule: str | None
    discount_rate: Decimal
    discount: Decimal
    taxable_amount: Decimal
    vat_rate: Decimal
    tax: Decimal
    total: Decimal
