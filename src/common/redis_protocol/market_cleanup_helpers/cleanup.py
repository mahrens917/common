"""Expired market cleanup for Kalshi and Deribit."""

import logging

from common.redis_protocol.typing import RedisClient, ensure_awaitable

from .cleanup_helpers import expiration_checker

logger = logging.getLogger(__name__)

# Constants
MIN_DERIBIT_KEY_PARTS = 5  # Minimum parts in deribit option key (markets:deribit:option:CURRENCY:EXPIRY:...)


class ExpiredMarketCleaner:
    """Clean up expired markets from Redis."""

    def __init__(self, redis_client: RedisClient, *, grace_period_days: int = 0) -> None:
        """
        Initialize cleaner.

        Args:
            redis_client: Redis client instance
            grace_period_days: Days after expiration to keep markets (default: 0)
        """
        self._redis = redis_client
        self._grace_period_days = grace_period_days

    async def cleanup_kalshi_markets(self) -> int:
        """
        Clean up expired Kalshi markets.

        Returns:
            Number of markets deleted
        """
        pattern = "markets:kalshi:*"
        deleted_count = 0

        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match=pattern, count=100))

            for key in keys:
                if await self._process_kalshi_market_key(key):
                    deleted_count += 1

            if cursor == 0:
                break

        if deleted_count > 0:
            logger.info("Cleaned up %d expired Kalshi markets", deleted_count)

        return deleted_count

    async def _process_kalshi_market_key(self, key) -> bool:
        """Process a single Kalshi market key and delete if expired."""
        key_str = key.decode() if isinstance(key, bytes) else str(key)

        market_data = await ensure_awaitable(self._redis.hgetall(key_str))
        if not market_data:
            return False

        expiration_time_str = expiration_checker.extract_expiration_time(market_data)
        if not expiration_time_str:
            return False

        if expiration_checker.is_expired_kalshi(expiration_time_str, self._grace_period_days):
            await ensure_awaitable(self._redis.delete(key_str))
            logger.debug("Deleted expired Kalshi market: %s", key_str)
            return True

        return False

    async def cleanup_deribit_options(self) -> int:
        """
        Clean up expired Deribit options.

        Returns:
            Number of options deleted
        """
        return await self._cleanup_deribit_instruments("option")

    async def cleanup_deribit_futures(self) -> int:
        """
        Clean up expired Deribit futures (excludes perpetuals).

        Returns:
            Number of futures deleted
        """
        return await self._cleanup_deribit_instruments("future")

    async def _cleanup_deribit_instruments(self, instrument_type: str) -> int:
        """
        Clean up expired Deribit instruments of the specified type.

        Args:
            instrument_type: "option" or "future"

        Returns:
            Number of instruments deleted
        """
        pattern = f"markets:deribit:{instrument_type}:*"
        deleted_count = 0

        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match=pattern, count=100))

            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)

                parts = key_str.split(":")
                if len(parts) < MIN_DERIBIT_KEY_PARTS:
                    continue

                expiry_str = parts[4]

                # Skip perpetual futures (no expiry date)
                if expiry_str.lower() == "perpetual":
                    continue

                if expiration_checker.is_expired_deribit(expiry_str, self._grace_period_days):
                    await ensure_awaitable(self._redis.delete(key_str))
                    deleted_count += 1
                    logger.debug("Deleted expired Deribit %s: %s", instrument_type, key_str)

            if cursor == 0:
                break

        if deleted_count > 0:
            logger.info("Cleaned up %d expired Deribit %ss", deleted_count, instrument_type)

        return deleted_count
