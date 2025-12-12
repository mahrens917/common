"""
Metadata write operations for Kalshi markets.

This module handles writing and updating market metadata in Redis.
"""

import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from ....redis_schema import KalshiMarketDescriptor
from ...error_types import REDIS_ERRORS
from ...market_metadata_builder import build_market_metadata
from ...typing import ensure_awaitable
from ..connection import RedisConnectionManager
from ..metadata import KalshiMetadataAdapter

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Handles metadata write operations for Kalshi markets."""

    def __init__(
        self,
        redis_connection: Optional[Redis],
        logger_instance: logging.Logger,
        metadata_adapter: KalshiMetadataAdapter,
        connection_manager: Optional[RedisConnectionManager] = None,
    ):
        """
        Initialize MetadataWriter.

        Args:
            redis_connection: Active Redis connection
            logger_instance: Logger instance
            metadata_adapter: Metadata adapter for market data processing
        """
        self.redis = redis_connection
        self.logger = logger_instance
        self._metadata = metadata_adapter
        self._connection = connection_manager

    async def store_market_metadata(
        self,
        market_ticker: str,
        market_data: Dict,
        event_data: Optional[Dict],
        descriptor: KalshiMarketDescriptor,
        weather_resolver: Any,
    ) -> bool:  # pragma: no cover - integration write path
        """
        Store market metadata in Redis using direct field updates.
        Only updates the specific fields provided by the Kalshi API, never touches weather or trading fields.

        Args:
            market_ticker: Market ticker
            market_data: Market data dictionary from Kalshi API
            event_data: Event data dictionary (optional)
            descriptor: Market descriptor
            weather_resolver: Weather station resolver

        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = self.redis
            if redis_client is None:
                if self._connection is None:
                    raise RuntimeError("Redis connection not initialized for MetadataWriter")
                redis_client = await self._connection.get_redis()

            market_key = descriptor.key

            # Build metadata from Kalshi API data only
            metadata = self._build_kalshi_metadata(market_ticker, market_data, event_data, descriptor, weather_resolver)

            # Direct update - only touch Kalshi API fields
            await ensure_awaitable(redis_client.hset(market_key, mapping=metadata))
            logger.debug(f"Updated {len(metadata)} Kalshi API fields for {market_ticker}")

        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error storing market metadata for %s: %s", market_ticker, exc, exc_info=True)
            raise
        else:
            return True

    def _build_kalshi_metadata(
        self,
        market_ticker: str,
        market_data: Dict,
        event_data: Optional[Dict],
        descriptor: KalshiMarketDescriptor,
        weather_resolver: Any,
    ) -> Dict[str, str]:
        """Build metadata dictionary from Kalshi API data."""
        return build_market_metadata(
            market_ticker=market_ticker,
            market_data=market_data,
            event_data=event_data,
            descriptor=descriptor,
            weather_resolver=weather_resolver,
            logger=self.logger,
        )
