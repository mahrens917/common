"""
Subscription tracking write operations.

This module handles tracking and persisting subscription state data.
"""

import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from ....redis_schema import KalshiMarketDescriptor

logger = logging.getLogger(__name__)


class SubscriptionWriter:
    """Handles subscription tracking write operations."""

    def __init__(
        self,
        redis_connection: Redis,
        logger_instance: logging.Logger,
        metadata_adapter: Any,
    ):
        self.redis = redis_connection
        self.logger = logger_instance
        self._metadata = metadata_adapter

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """Extract weather station ICAO code from KXHIGH market ticker with alias support."""
        return self._metadata.extract_weather_station_from_ticker(market_ticker)

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any], descriptor: KalshiMarketDescriptor) -> str:
        """Ensure we have an ISO formatted expiry/close time for downstream consumers."""
        expiry_token = descriptor.expiry_token
        if not expiry_token:
            return self._metadata.derive_expiry_iso(market_ticker, metadata, None)
        return self._metadata.derive_expiry_iso(market_ticker, metadata, expiry_token)

    def ensure_market_metadata_fields(self, market_ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Populate essential metadata fields when REST ingestion is missing."""
        return self._metadata.ensure_market_metadata_fields(market_ticker, metadata)
