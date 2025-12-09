"""
Subscription tracking write operations.

This module handles tracking and persisting subscription state data.
"""

import logging
from typing import Any, Dict, List, Optional

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
        """
        Initialize SubscriptionWriter.

        Args:
            redis_connection: Active Redis connection
            logger_instance: Logger instance
            metadata_adapter: Metadata adapter for market data processing
        """
        self.redis = redis_connection
        self.logger = logger_instance
        self._metadata = metadata_adapter

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """
        Extract weather station ICAO code from KXHIGH market ticker with alias support.

        Args:
            market_ticker: Market ticker (e.g., KXHIGHPHIL-25AUG31-B80.5 or KXHIGHAUSHAUS-25AUG30-T100)

        Returns:
            4-letter ICAO weather station code or None if not found
        """
        return self._metadata.extract_weather_station_from_ticker(market_ticker)

    def derive_expiry_iso(
        self, market_ticker: str, metadata: Dict[str, Any], descriptor: KalshiMarketDescriptor
    ) -> str:
        """Ensure we have an ISO formatted expiry/close time for downstream consumers."""
        return self._metadata.derive_expiry_iso(
            market_ticker,
            metadata,
            descriptor.expiry_token,
        )

    def ensure_market_metadata_fields(
        self, market_ticker: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Populate essential metadata fields when REST ingestion is missing."""
        return self._metadata.ensure_market_metadata_fields(market_ticker, metadata)

    @staticmethod
    def select_timestamp_value(market_data: Dict, fields: List[str]) -> Optional[object]:
        """Select timestamp value from market data."""
        from ..metadata_helpers.timestamp_normalization import select_timestamp_value

        return select_timestamp_value(market_data, fields)

    @staticmethod
    def normalize_timestamp(value: Any) -> Optional[str]:
        """Normalize timestamp value."""
        from ..metadata_helpers.timestamp_normalization import normalize_timestamp

        return normalize_timestamp(value)
