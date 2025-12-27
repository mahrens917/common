"""Type definitions for Kalshi market catalog discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DiscoveredMarket:
    """A discovered market within an event."""

    ticker: str
    close_time: str
    cap_strike: float | None
    floor_strike: float | None
    raw_data: Dict[str, Any] = field(repr=False)


@dataclass
class DiscoveredEvent:
    """A discovered mutually exclusive event with its markets."""

    event_ticker: str
    title: str
    category: str
    mutually_exclusive: bool
    markets: List[DiscoveredMarket]


class CatalogDiscoveryError(RuntimeError):
    """Raised when catalog discovery fails."""


class StrikeValidationError(ValueError):
    """Raised when market strike validation fails."""


__all__ = [
    "CatalogDiscoveryError",
    "DiscoveredEvent",
    "DiscoveredMarket",
    "StrikeValidationError",
]
