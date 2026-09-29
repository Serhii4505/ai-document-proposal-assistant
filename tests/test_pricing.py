from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
import pytest

from app.pricing.catalog import load_catalog
from app.pricing.engine import PricingEngine, VolumeDiscountRule
from app.pricing.errors import CatalogError, InactiveServiceError, MinimumQuantityError, PricingError, UnknownServiceError
from app.pricing.models import RequestedService


HEADER = "service_code,service_name,unit,unit_price,minimum_quantity,active,currency\n"


def _csv(path: Path, rows: str) -> Path:
    path.write_text(HEADER + rows, encoding="utf-8")
    return path


def test_imports_csv_and_calculates_vat(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "AUTO_SETUP,Automation setup,project,1000.00,1,true,EUR\nTRAINING,Staff training,session,250.00,1,true,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path), vat_rate=Decimal("0.23"))

    result = engine.calculate([RequestedService(service_code="auto_setup", quantity=1), RequestedService(service_code="TRAINING", quantity=2)])

    assert result.subtotal == Decimal("1500.00")
    assert result.tax == Decimal("345.00")
    assert result.total == Decimal("1845.00")
    assert result.discount == Decimal("0.00")


def test_volume_discount_applies_at_threshold_before_vat(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "AUTO_SETUP,Automation setup,project,1500.00,1,true,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path), vat_rate=Decimal("0.23"), discount_rule=VolumeDiscountRule())

    result = engine.calculate([RequestedService(service_code="AUTO_SETUP", quantity=2)])

    assert result.subtotal == Decimal("3000.00")
    assert result.discount_rule == "volume_10_percent"
    assert result.discount == Decimal("300.00")
    assert result.taxable_amount == Decimal("2700.00")
    assert result.tax == Decimal("621.00")
    assert result.total == Decimal("3321.00")


def test_rounds_money_half_up(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "UNIT_TEST,Unit test,item,0.05,1,true,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path), vat_rate=Decimal("0.23"))

    result = engine.calculate([RequestedService(service_code="UNIT_TEST", quantity=1)])

    assert result.tax == Decimal("0.01")
    assert result.total == Decimal("0.06")


def test_imports_xlsx_catalogue(tmp_path: Path) -> None:
    path = tmp_path / "prices.xlsx"
    workbook = Workbook(); sheet = workbook.active
    sheet.append(HEADER.strip().split(",")); sheet.append(["SUPPORT", "Support package", "month", 500, 1, True, "EUR"])
    workbook.save(path)

    catalog = load_catalog(path, allowed_root=tmp_path)

    assert catalog.currency == "EUR"
    assert catalog.items["SUPPORT"].unit_price == Decimal("500")


def test_rejects_unknown_inactive_and_low_quantity(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "ACTIVE,Active service,item,100.00,2,true,EUR\nINACTIVE,Inactive service,item,100.00,1,false,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path))

    with pytest.raises(UnknownServiceError): engine.calculate([RequestedService(service_code="MISSING", quantity=1)])
    with pytest.raises(InactiveServiceError): engine.calculate([RequestedService(service_code="INACTIVE", quantity=1)])
    with pytest.raises(MinimumQuantityError): engine.calculate([RequestedService(service_code="ACTIVE", quantity=1)])


def test_rejects_duplicate_requested_codes(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "SERVICE,Service,item,100.00,1,true,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path))
    with pytest.raises(PricingError, match="Duplicate"):
        engine.calculate([RequestedService(service_code="SERVICE", quantity=1), RequestedService(service_code="service", quantity=2)])


@pytest.mark.parametrize("rows", [
    "DUP,First,item,100.00,1,true,EUR\nDUP,Second,item,200.00,1,true,EUR\n",
    "A,First,item,100.00,1,true,EUR\nB,Second,item,200.00,1,true,USD\n",
    "BAD,Bad price,item,not-a-price,1,true,EUR\n",
])
def test_rejects_invalid_catalogues(tmp_path: Path, rows: str) -> None:
    path = _csv(tmp_path / "prices.csv", rows)
    with pytest.raises(CatalogError):
        load_catalog(path, allowed_root=tmp_path)


def test_ai_cannot_override_catalogue_price(tmp_path: Path) -> None:
    path = _csv(tmp_path / "prices.csv", "SERVICE,Approved service,item,125.00,1,true,EUR\n")
    engine = PricingEngine(load_catalog(path, allowed_root=tmp_path))

    result = engine.calculate([RequestedService(service_code="SERVICE", quantity=2)])

    assert result.line_items[0].unit_price == Decimal("125.00")
    assert result.subtotal == Decimal("250.00")

