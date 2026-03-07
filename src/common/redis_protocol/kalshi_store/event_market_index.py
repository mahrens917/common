"""In-memory index mapping event_ticker to market data.

Built once on startup from a full KalshiStore scan, then updated
incrementally as stream messages arrive — avoids reloading all 500+
markets on every orderbook change.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from common.redis_schema import build_kalshi_market_key

logger = logging.getLogger(__name__)

_KALSHI_SCAN_PATTERN = "markets:kalshi:*"
_KALSHI_SUBKEY_EXCLUDES = (":trading_signal", ":position_state")
_RECONCILE_TOLERANCE = 5


async def _count_kalshi_keys(redis: Any) -> int:
    """SCAN-count Redis keys matching the Kalshi market pattern."""
    count = 0
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=_KALSHI_SCAN_PATTERN, count=500)
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            if not any(ex in key_str for ex in _KALSHI_SUBKEY_EXCLUDES):
                count += 1
        if cursor == 0:
            break
    return count


class EventMarketIndex:
    """In-memory index: event_ticker -> market data.

    Built once on startup, updated incrementally from stream messages.
    """

    def __init__(self) -> None:
        self._event_to_tickers: Dict[str, set[str]] = {}
        self._ticker_to_event: Dict[str, str] = {}
        self._market_cache: Dict[str, Dict[str, Any]] = {}

    async def initialize(self, kalshi_store: Any) -> None:
        """One-time full scan to build index."""
        markets = await kalshi_store.get_all_markets()
        for market in markets:
            market_ticker = market.get("market_ticker") or market.get("ticker")
            event_ticker = market.get("event_ticker")
            if not market_ticker or not event_ticker:
                continue
            self._register(event_ticker, market_ticker)
            self._market_cache[market_ticker] = market
        logger.info(
            "EventMarketIndex initialized: %d events, %d markets",
            len(self._event_to_tickers),
            len(self._market_cache),
        )

    async def refresh_market(self, redis: Any, market_ticker: str) -> Optional[Dict[str, Any]]:
        """Re-read single market hash after orderbook update (1 HGETALL).

        Returns the updated market data dict, or None if the market
        no longer exists in Redis.
        """
        market_key = build_kalshi_market_key(market_ticker)
        raw = await redis.hgetall(market_key)
        if not raw:
            return None
        decoded = _decode_hash(raw)
        decoded["market_ticker"] = market_ticker
        decoded["market_key"] = market_key
        self._market_cache[market_ticker] = decoded
        return decoded

    def apply_stream_update(self, market_ticker: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Merge stream payload into in-memory cache. No Redis IO.

        Cache hit: merges fields into existing entry, returns it.
        Cache miss with event_ticker in fields: creates new entry, registers mapping.
        Cache miss without event_ticker: returns None (caller should re-initialize).
        """
        existing = self._market_cache.get(market_ticker)
        if existing is not None:
            existing.update(fields)
            return existing

        event_ticker = fields.get("event_ticker")
        if not event_ticker:
            return None

        entry: Dict[str, Any] = {"market_ticker": market_ticker, **fields}
        self._market_cache[market_ticker] = entry
        self._register(str(event_ticker), market_ticker)
        return entry

    def get_market(self, market_ticker: str) -> Optional[Dict[str, Any]]:
        """Return cached market data for a single ticker, or None."""
        return self._market_cache.get(market_ticker)

    def get_all_tickers(self) -> List[str]:
        """Return all cached market tickers."""
        return list(self._market_cache.keys())

    def get_all_markets(self) -> List[Dict[str, Any]]:
        """Return all cached market data dicts."""
        return list(self._market_cache.values())

    def get_event_markets(self, event_ticker: str) -> List[Dict[str, Any]]:
        """Return cached market data for one event."""
        tickers = self._event_to_tickers.get(event_ticker)
        if not tickers:
            return []
        return [self._market_cache[t] for t in tickers if t in self._market_cache]

    def get_event_market_tickers(self, event_ticker: str) -> set[str]:
        """Return the set of market tickers belonging to an event."""
        return set(self._event_to_tickers.get(event_ticker, set()))

    def update_index(self, event_ticker: str, market_ticker: str) -> None:
        """Register a market_ticker under an event_ticker."""
        self._register(event_ticker, market_ticker)

    @property
    def event_count(self) -> int:
        """Number of indexed events."""
        return len(self._event_to_tickers)

    @property
    def market_count(self) -> int:
        """Number of indexed markets."""
        return len(self._market_cache)

    async def reconcile(self, redis: Any) -> bool:
        """Compare cache count to Redis; return True if diverged."""
        redis_count = await _count_kalshi_keys(redis)
        if abs(redis_count - self.market_count) <= _RECONCILE_TOLERANCE:
            return False
        logger.warning(
            "EventMarketIndex count divergence: cache=%d redis=%d — caller should re-initialize",
            self.market_count,
            redis_count,
        )
        return True

    def _register(self, event_ticker: str, market_ticker: str) -> None:
        """Internal registration of event<->market mapping."""
        if event_ticker not in self._event_to_tickers:
            self._event_to_tickers[event_ticker] = set()
        self._event_to_tickers[event_ticker].add(market_ticker)
        self._ticker_to_event[market_ticker] = event_ticker


def _decode_hash(raw: Dict[Any, Any]) -> Dict[str, Any]:
    """Decode Redis hash bytes to strings."""
    decoded: Dict[str, Any] = {}
    for k, v in raw.items():
        key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
        val = v.decode("utf-8") if isinstance(v, bytes) else v
        decoded[key] = val
    return decoded


__all__ = ["EventMarketIndex"]
