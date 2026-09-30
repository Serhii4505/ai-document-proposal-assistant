from decimal import Decimal

import pytest

from app.config import ConfigurationError, get_settings


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CURRENCY", "VAT_RATE", "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.company_name == "Northstar Automation"
    assert settings.currency == "EUR"
    assert settings.vat_rate == Decimal("0.23")
    assert settings.gemini_api_key is None


def test_rejects_invalid_vat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAT_RATE", "1.50")
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError, match="between 0 and 1"):
        get_settings()

    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("name", "raw_value"),
    [
        ("VAT_RATE", "NaN"),
        ("VAT_RATE", "Infinity"),
        ("VOLUME_DISCOUNT_THRESHOLD", "Infinity"),
    ],
)
def test_rejects_non_finite_decimals(
    monkeypatch: pytest.MonkeyPatch, name: str, raw_value: str
) -> None:
    monkeypatch.setenv(name, raw_value)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError, match="finite decimal number"):
        get_settings()

    get_settings.cache_clear()
