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
        """Initialize cleaner."""
        self._redis = redis_client
        self._grace_period_days = grace_period_days

    async def cleanup_kalshi_markets(self) -> int:
        """Clean up expired Kalshi markets."""
        pattern = "markets:kalshi:*"
        all_keys: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match=pattern, count=100))
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                all_keys.append(key_str)
            if cursor == 0:
                break

        if not all_keys:
            return 0

        # Pipeline hgetall for all keys in batches
        _BATCH_SIZE = 200
        deleted_count = 0
        for i in range(0, len(all_keys), _BATCH_SIZE):
            batch = all_keys[i : i + _BATCH_SIZE]
            pipe = self._redis.pipeline()
            for key_str in batch:
                pipe.hgetall(key_str)
            results = await ensure_awaitable(pipe.execute())

            keys_to_delete: list[str] = []
            for key_str, market_data in zip(batch, results):
                if not market_data:
                    continue
                expiration_time_str = expiration_checker.extract_expiration_time(market_data)
                if not expiration_time_str:
                    continue
                if expiration_checker.is_expired_kalshi(expiration_time_str, self._grace_period_days):
                    keys_to_delete.append(key_str)

            if keys_to_delete:
                del_pipe = self._redis.pipeline()
                for key_str in keys_to_delete:
                    del_pipe.delete(key_str)
                await ensure_awaitable(del_pipe.execute())
                deleted_count += len(keys_to_delete)
                for key_str in keys_to_delete:
                    logger.debug("Deleted expired Kalshi market: %s", key_str)

        if deleted_count > 0:
            logger.info("Cleaned up %d expired Kalshi markets", deleted_count)

        return deleted_count

    async def cleanup_deribit_options(self) -> int:
        """Clean up expired Deribit options."""
        return await self._cleanup_deribit_instruments("option")

    async def cleanup_deribit_futures(self) -> int:
        """Clean up expired Deribit futures (excludes perpetuals)."""
        return await self._cleanup_deribit_instruments("future")

    async def _cleanup_deribit_instruments(self, instrument_type: str) -> int:
        """Clean up expired Deribit instruments of the specified type."""
        pattern = f"markets:deribit:{instrument_type}:*"
        keys_to_delete: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match=pattern, count=100))
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                parts = key_str.split(":")
                if len(parts) < MIN_DERIBIT_KEY_PARTS:
                    continue
                expiry_str = parts[4]
                if expiry_str.lower() == "perpetual":
                    continue
                if expiration_checker.is_expired_deribit(expiry_str, self._grace_period_days):
                    keys_to_delete.append(key_str)
            if cursor == 0:
                break

        if keys_to_delete:
            pipe = self._redis.pipeline()
            for key_str in keys_to_delete:
                pipe.delete(key_str)
            await ensure_awaitable(pipe.execute())
            for key_str in keys_to_delete:
                logger.debug("Deleted expired Deribit %s: %s", instrument_type, key_str)
            logger.info("Cleaned up %d expired Deribit %ss", len(keys_to_delete), instrument_type)

        return len(keys_to_delete)
