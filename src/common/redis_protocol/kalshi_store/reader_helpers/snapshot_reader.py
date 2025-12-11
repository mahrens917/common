"""
Snapshot Reader - Read market snapshots and metadata

Slim coordinator that delegates to helper modules.
"""

import logging
from typing import Any, Dict, Set

from redis.asyncio import Redis

from . import snapshotreader_helpers as helpers

logger = logging.getLogger(__name__)


class SnapshotReader:
    """Read market snapshots and metadata from Redis"""

    def __init__(self, logger_instance: logging.Logger, metadata_extractor, metadata_adapter):
        """
        Initialize snapshot reader

        Args:
            logger_instance: Logger to use for read operations
            metadata_extractor: MetadataExtractor instance
            metadata_adapter: KalshiMetadataAdapter instance
        """
        self.logger = logger_instance
        self._metadata_extractor = metadata_extractor
        self._metadata_adapter = metadata_adapter

    async def get_subscribed_markets(self, redis: Redis, subscriptions_key: str) -> Set[str]:  # pragma: no cover - Redis coordination
        """Return the set of market tickers currently subscribed across all services."""
        return await helpers.get_subscribed_markets(redis, subscriptions_key)

    async def is_market_tracked(self, redis: Redis, market_key: str, market_ticker: str) -> bool:
        """Check if a market is tracked (check if market data exists)"""
        return await helpers.is_market_tracked(redis, market_key, market_ticker)

    async def get_market_snapshot(self, redis: Redis, market_key: str, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Return the canonical Redis hash for a Kalshi market ticker."""
        return await helpers.get_market_snapshot(redis, market_key, ticker, self._metadata_extractor, include_orderbook=include_orderbook)

    async def get_market_metadata(self, redis: Redis, market_key: str, ticker: str) -> Dict:
        """Get all metadata fields for a market"""
        return await helpers.get_market_metadata(redis, market_key, ticker, self._metadata_extractor, self._metadata_adapter)

    async def get_market_field(self, redis: Redis, market_key: str, ticker: str, field: str) -> str:
        """Get specific market field"""
        return await helpers.get_market_field(redis, market_key, ticker, field)
