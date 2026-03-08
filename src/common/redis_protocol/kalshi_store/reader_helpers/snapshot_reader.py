"""
Snapshot Reader - Read market snapshots and metadata
"""

import logging
from typing import Any, Dict, Set

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from ..store_initializer import KalshiStoreError

__all__ = ["KalshiStoreError", "SnapshotReader"]

logger = logging.getLogger(__name__)

_CONST_2 = 2


class SnapshotReader:
    """Read market snapshots and metadata from Redis"""

    def __init__(self, logger_instance: logging.Logger, metadata_extractor, metadata_adapter):
        self.logger = logger_instance
        self._metadata_extractor = metadata_extractor
        self._metadata_adapter = metadata_adapter

    async def get_subscribed_markets(self, redis: Redis, subscriptions_key: str) -> Set[str]:  # pragma: no cover - Redis coordination
        """Return the set of market tickers currently subscribed across all services.

        Raises on Redis error.
        """
        try:
            subscriptions = await ensure_awaitable(redis.hgetall(subscriptions_key))
            markets = set()
            for key, _value in subscriptions.items():
                key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                parts = key_str.split(":", 1)
                if len(parts) == _CONST_2:
                    markets.add(parts[1])
        except REDIS_ERRORS as exc:
            logger.error("Error getting subscribed markets: %s", exc, exc_info=True)
            raise
        else:
            return markets

    async def is_market_tracked(self, redis: Redis, market_key: str, market_ticker: str) -> bool:
        """Check if a market is tracked (check if market data exists).

        Raises on Redis error.
        """
        try:
            return await redis.exists(market_key)
        except REDIS_ERRORS as exc:
            logger.error(
                "Error checking if market %s is tracked: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
            raise

    async def get_market_snapshot(self, redis: Redis, market_key: str, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Return the canonical Redis hash for a Kalshi market ticker.

        Raises KalshiStoreError if snapshot cannot be retrieved.
        """
        if not ticker:
            raise TypeError("ticker must be provided for get_market_snapshot")

        try:
            raw_snapshot = await ensure_awaitable(redis.hgetall(market_key))
        except REDIS_ERRORS as exc:
            raise KalshiStoreError(f"Redis error retrieving snapshot for {ticker}") from exc

        if not raw_snapshot:
            raise KalshiStoreError(f"Kalshi market {ticker} snapshot missing in Redis")

        snapshot = self._metadata_extractor.normalize_hash(raw_snapshot)
        self._metadata_extractor.sync_top_of_book_fields(snapshot)

        if not include_orderbook:
            for field_name in ("yes_bids", "yes_asks", "no_bids", "no_asks"):
                snapshot.pop(field_name, None)

        return snapshot

    async def get_market_metadata(self, redis: Redis, market_key: str, ticker: str) -> Dict:
        """Get all metadata fields for a market"""
        snapshot = await self.get_market_snapshot(redis, market_key, ticker, include_orderbook=False)
        if not snapshot:
            return {}

        enriched = self._metadata_adapter.ensure_market_metadata_fields(ticker, snapshot)
        for field_name in ("yes_bids", "yes_asks", "no_bids", "no_asks"):
            enriched.pop(field_name, None)
        return enriched

    async def get_market_field(self, redis: Redis, market_key: str, ticker: str, field: str) -> str:
        """Get specific market field. Returns empty string if not found."""
        try:
            result = await ensure_awaitable(redis.hget(market_key, field))
            if result:
                return result
            else:
                return ""
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error("Redis error getting field %s for %s: %s", field, ticker, exc, exc_info=True)
            return ""
