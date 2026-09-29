"""Explicit pricing and catalogue errors."""


class PricingError(ValueError):
    """Base class for deterministic pricing failures."""


class CatalogError(PricingError):
    """The approved catalogue is invalid or inconsistent."""


class UnknownServiceError(PricingError):
    """A requested service does not exist in the catalogue."""


class InactiveServiceError(PricingError):
    """A requested service is not active."""


class MinimumQuantityError(PricingError):
    """A requested quantity is below the catalogue minimum."""

