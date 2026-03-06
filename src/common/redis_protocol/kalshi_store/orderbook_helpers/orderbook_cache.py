"""In-memory cache of per-market hash fields for orderbook processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MarketUpdate:
    """Value type for the CoalescingBatcher flush callback."""

    market_key: str
    market_ticker: str
    fields: Dict[str, str]
    timestamp: str


class OrderbookCache:
    """Cache of per-market hash fields. Deltas read/write here instead of Redis."""

    def __init__(self) -> None:
        self._markets: Dict[str, Dict[str, str]] = {}

    def get_field(self, market_key: str, field: str) -> str | None:
        """Return a single cached field value, or None if not present."""
        entry = self._markets.get(market_key)
        if entry is None:
            return None
        return entry.get(field)

    def store_snapshot(self, market_key: str, fields: Dict[str, str]) -> None:
        """Replace all cached fields for a market with a full snapshot.

        Takes ownership of *fields* — callers must not mutate the dict after passing it.
        """
        self._markets[market_key] = fields

    def update_fields(self, market_key: str, fields: Dict[str, str]) -> Dict[str, str]:
        """Update specific fields and return the full market state by reference.

        Callers must not mutate the returned dict.
        """
        if market_key not in self._markets:
            self._markets[market_key] = {}
        entry = self._markets[market_key]
        entry.update(fields)
        return entry

    def get_snapshot(self, market_key: str) -> Dict[str, str] | None:
        """Return the cached fields for a market, or None.

        Callers must not mutate the returned dict.
        """
        return self._markets.get(market_key)
