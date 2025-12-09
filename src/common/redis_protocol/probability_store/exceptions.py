from __future__ import annotations

"""Custom exceptions for the probability store."""


from typing import Optional


class ProbabilityStoreError(RuntimeError):
    """Base error for probability store failures."""


class ProbabilityStoreInitializationError(ProbabilityStoreError):
    """Raised when Redis connectivity has not been initialised."""

    def __init__(self, message: str = "Redis connection not initialised") -> None:
        super().__init__(message)


class ProbabilityStoreVerificationError(ProbabilityStoreError):
    """Raised when verification of stored probabilities fails."""


class ProbabilityDataNotFoundError(ProbabilityStoreError):
    """Raised when requested probability payloads are missing."""

    def __init__(self, currency: str, context: Optional[str] = None) -> None:
        detail = f"No probability data found for {currency.upper()}"
        if context:
            detail = f"{detail} ({context})"
        super().__init__(detail)
