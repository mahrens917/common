"""Shared error types for Kalshi API helpers."""

from typing import Any


class KalshiErrorBase(RuntimeError):
    """Base error that attaches provided keyword fields as attributes."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message)
        for key, value in kwargs.items():
            setattr(self, key, value)


class KalshiClientError(KalshiErrorBase):
    """Raised when Kalshi REST operations fail."""
