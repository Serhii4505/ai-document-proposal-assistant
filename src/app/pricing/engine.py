"""Authoritative Decimal-based pricing rules."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.pricing.catalog import ServiceCatalog
from app.pricing.errors import InactiveServiceError, MinimumQuantityError, PricingError, UnknownServiceError
from app.pricing.models import PricedLine, PricingResult, RequestedService


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class VolumeDiscountRule:
    threshold: Decimal = Decimal("3000.00")
    rate: Decimal = Decimal("0.10")
    name: str = "volume_10_percent"

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError("Discount threshold must be positive")
        if self.rate < 0 or self.rate > 1:
            raise ValueError("Discount rate must be between 0 and 1")

    def calculate(self, subtotal: Decimal) -> Decimal:
        return money(subtotal * self.rate) if subtotal >= self.threshold else Decimal("0.00")


class PricingEngine:
    def __init__(self, catalog: ServiceCatalog, *, vat_rate: Decimal = Decimal("0.23"), discount_rule: VolumeDiscountRule | None = None) -> None:
        if vat_rate < 0 or vat_rate > 1:
            raise ValueError("VAT rate must be between 0 and 1")
        self.catalog = catalog
        self.vat_rate = vat_rate
        self.discount_rule = discount_rule

    def calculate(self, requested: list[RequestedService]) -> PricingResult:
        if not requested:
            raise PricingError("At least one service is required")
        codes = [item.service_code for item in requested]
        if len(codes) != len(set(codes)):
            raise PricingError("Duplicate service codes are not allowed")

        lines: list[PricedLine] = []
        for request in requested:
            item = self.catalog.get(request.service_code)
            if item is None:
                raise UnknownServiceError(f"Unknown service code: {request.service_code}")
            if not item.active:
                raise InactiveServiceError(f"Inactive service code: {request.service_code}")
            if request.quantity < item.minimum_quantity:
                raise MinimumQuantityError(f"{request.service_code} requires minimum quantity {item.minimum_quantity}")
            lines.append(PricedLine(service_code=item.service_code, service_name=item.service_name, unit=item.unit, quantity=request.quantity, unit_price=money(item.unit_price), line_total=money(item.unit_price * request.quantity)))

        subtotal = money(sum((line.line_total for line in lines), Decimal("0")))
        discount = self.discount_rule.calculate(subtotal) if self.discount_rule else Decimal("0.00")
        taxable = money(subtotal - discount)
        tax = money(taxable * self.vat_rate)
        total = money(taxable + tax)
        return PricingResult(currency=self.catalog.currency, line_items=lines, subtotal=subtotal, discount_rule=self.discount_rule.name if discount > 0 and self.discount_rule else None, discount_rate=self.discount_rule.rate if discount > 0 and self.discount_rule else Decimal("0"), discount=discount, taxable_amount=taxable, vat_rate=self.vat_rate, tax=tax, total=total)

