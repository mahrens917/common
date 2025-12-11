"""Market status checking helper for KalshiMarketReader."""

from typing import Any, Dict, Optional

from .expiry_checker import ExpiryChecker
from .ticker_parser import TickerParser


class MarketStatusChecker:
    """Checks market status (expiry, settlement)."""

    def __init__(self, conn_wrapper, ticker_parser: TickerParser, expiry_checker: ExpiryChecker, get_key_fn):
        self._conn = conn_wrapper
        self._ticker_parser = ticker_parser
        self._expiry_checker = expiry_checker
        self._get_key = get_key_fn

    async def is_expired(self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Check if market is expired."""
        _ = metadata
        if not await self._conn.ensure_connection():
            return False
        ticker = self._ticker_parser.normalize_ticker(market_ticker)
        redis = await self._conn.get_redis()
        return await self._expiry_checker.is_market_expired(redis, self._get_key(ticker), ticker)

    async def is_settled(self, market_ticker: str) -> bool:
        """Check if market is settled."""
        if not await self._conn.ensure_connection():
            return False
        ticker = self._ticker_parser.normalize_ticker(market_ticker)
        redis = await self._conn.get_redis()
        return await self._expiry_checker.is_market_settled(redis, self._get_key(ticker), ticker)
