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
