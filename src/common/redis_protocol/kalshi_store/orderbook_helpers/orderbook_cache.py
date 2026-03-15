"""In-memory cache of per-market hash fields for orderbook processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

_EMPTY_SIDE_DATA: Dict[str, Any] = {}


@dataclass(frozen=True)
class MarketUpdate:
    """Snapshot of a market update for Redis writes."""

    market_key: str
    market_ticker: str
    fields: Dict[str, Any]
    timestamp: str


class OrderbookCache:
    """Cache of per-market hash fields. Deltas read/write here instead of Redis.

    Side data fields (yes_bids, yes_asks) are stored as raw Python dicts.
    All other fields are stored as strings. Serialization to JSON happens
    only at write time.
    """

    def __init__(self) -> None:
        self._markets: Dict[str, Dict[str, Any]] = {}
        self._previous_bests: Dict[str, tuple[Any, Any]] = {}
        self._event_tickers: Dict[str, str] = {}
        self._stream_publish_count = 0
        self._exchange_message_count = 0

    def get_field(self, market_key: str, field: str) -> Any | None:
        """Return a single cached field value, or None if not present."""
        entry = self._markets.get(market_key)
        if entry is None:
            return None
        return entry.get(field)

    def get_side_data(self, market_key: str, field: str) -> Dict[str, Any]:
        """Return the orderbook side dict for a field, or empty dict if absent."""
        entry = self._markets.get(market_key)
        if entry is None:
            return _EMPTY_SIDE_DATA
        value = entry.get(field)
        if not isinstance(value, dict):
            return _EMPTY_SIDE_DATA
        return value

    def store_snapshot(self, market_key: str, fields: Dict[str, Any]) -> None:
        """Replace all cached fields for a market with a full snapshot.

        Takes ownership of *fields* — callers must not mutate the dict after passing it.
        """
        self._markets[market_key] = fields

    def update_fields(self, market_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update specific fields and return the full market state by reference.

        Callers must not mutate the returned dict.
        """
        if market_key not in self._markets:
            self._markets[market_key] = {}
        entry = self._markets[market_key]
        entry.update(fields)
        return entry

    def get_snapshot(self, market_key: str) -> Dict[str, Any] | None:
        """Return the cached fields for a market, or None.

        Callers must not mutate the returned dict.
        """
        return self._markets.get(market_key)

    def check_price_changed(self, market_key: str) -> bool:
        """Compare current best prices against previous, return True if changed."""
        entry = self._markets.get(market_key)
        if entry is None:
            _none_guard_value = False
            return _none_guard_value
        current = (entry.get("yes_bid"), entry.get("yes_ask"))
        previous = self._previous_bests.get(market_key)
        self._previous_bests[market_key] = current
        return current != previous

    def get_event_ticker(self, market_key: str) -> str | None:
        """Return cached event_ticker for a market, or None."""
        return self._event_tickers.get(market_key)

    def set_event_ticker(self, market_key: str, event_ticker: str) -> None:
        """Cache an event_ticker for a market."""
        self._event_tickers[market_key] = event_ticker

    def record_stream_publish(self) -> None:
        """Increment the stream publish counter."""
        self._stream_publish_count += 1

    def drain_stream_publish_count(self) -> int:
        """Return and reset the stream publish counter."""
        count = self._stream_publish_count
        self._stream_publish_count = 0
        return count

    def record_exchange_message(self) -> None:
        """Increment the exchange message counter (all WS messages received)."""
        self._exchange_message_count += 1

    def drain_exchange_message_count(self) -> int:
        """Return and reset the exchange message counter."""
        count = self._exchange_message_count
        self._exchange_message_count = 0
        return count

    def remove_market(self, market_key: str) -> None:
        """Remove a market from the cache to free memory after unsubscribe."""
        self._markets.pop(market_key, None)
        self._previous_bests.pop(market_key, None)
        self._event_tickers.pop(market_key, None)
