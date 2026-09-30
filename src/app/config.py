"""Environment-based application configuration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class ConfigurationError(ValueError):
    """Raised when an environment value is missing or invalid."""


def _read_decimal(name: str, default: str) -> Decimal:
    raw_value = os.getenv(name, default).strip()
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ConfigurationError(f"{name} must be a decimal number") from exc
    if not value.is_finite():
        raise ConfigurationError(f"{name} must be a finite decimal number")

    if value < Decimal("0") or value > Decimal("1"):
        raise ConfigurationError(f"{name} must be between 0 and 1")
    return value


def _read_positive_decimal(name: str, default: str) -> Decimal:
    raw_value = os.getenv(name, default).strip()
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ConfigurationError(f"{name} must be a decimal number") from exc
    if not value.is_finite():
        raise ConfigurationError(f"{name} must be a finite decimal number")
    if value <= Decimal("0"):
        raise ConfigurationError(f"{name} must be greater than 0")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    app_version: str
    database_path: Path
    vector_database_path: Path
    proposal_output_dir: Path
    service_catalog_path: Path
    company_name: str
    currency: str
    vat_rate: Decimal
    volume_discount_threshold: Decimal
    volume_discount_rate: Decimal
    gemini_api_key: str | None
    gemini_embedding_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and validate settings once per process."""

    currency = os.getenv("CURRENCY", "EUR").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ConfigurationError("CURRENCY must be a three-letter code")

    database_path = Path(os.getenv("DATABASE_PATH", "data/app.db")).expanduser()
    if database_path.exists() and database_path.is_dir():
        raise ConfigurationError("DATABASE_PATH must point to a file")

    api_key = os.getenv("GEMINI_API_KEY", "").strip() or None

    return Settings(
        app_name=os.getenv("APP_NAME", "AI Document & Proposal Assistant").strip(),
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
        app_version=os.getenv("APP_VERSION", "0.1.0").strip(),
        database_path=database_path,
        vector_database_path=Path(os.getenv("VECTOR_DATABASE_PATH", "data/vectors.db")).expanduser(),
        proposal_output_dir=Path(os.getenv("PROPOSAL_OUTPUT_DIR", "output/proposals")).expanduser(),
        service_catalog_path=Path(os.getenv("SERVICE_CATALOG_PATH", "demo/service-catalog.csv")).expanduser(),
        company_name=os.getenv("COMPANY_NAME", "Northstar Automation").strip(),
        currency=currency,
        vat_rate=_read_decimal("VAT_RATE", "0.23"),
        volume_discount_threshold=_read_positive_decimal("VOLUME_DISCOUNT_THRESHOLD", "3000.00"),
        volume_discount_rate=_read_decimal("VOLUME_DISCOUNT_RATE", "0.10"),
        gemini_api_key=api_key,
        gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2").strip(),
    )
