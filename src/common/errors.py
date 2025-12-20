"""Common error types used across the codebase."""

from __future__ import annotations


class PricingValidationError(ValueError):
    """Raised when price validation fails."""

    def __init__(self, value: str, *, reason: str = "Invalid numeric value") -> None:
        message = f"{reason}: {value}"
        super().__init__(message)
        self.value = value
        self.reason = reason


__all__ = ["PricingValidationError"]
