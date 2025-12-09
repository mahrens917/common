"""Shared MarketSkip exception for Kalshi Store components."""

from typing import Optional


class MarketSkip(RuntimeError):
    """Signal why a market was skipped during aggregation."""

    def __init__(self, reason: str, detail: Optional[str] = None) -> None:
        self.reason = reason
        super().__init__(detail or reason)


__all__ = ["MarketSkip"]
