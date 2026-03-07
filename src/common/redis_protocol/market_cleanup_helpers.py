"""Expired market cleanup for Kalshi and Deribit."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from common.redis_protocol.typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)


def is_expired_kalshi(expiration_time_str: str, grace_period_days: int) -> bool:
    """Check if Kalshi market is expired beyond grace period."""
    try:
        expiration_time = datetime.fromisoformat(expiration_time_str.replace("Z", "+00:00"))
        if expiration_time.tzinfo is None:
            expiration_time = expiration_time.replace(tzinfo=timezone.utc)
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=grace_period_days)
    except (ValueError, AttributeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse Kalshi expiration time '%s': %s", expiration_time_str, exc)
        return False
    else:
        return expiration_time < cutoff_time


def is_expired_deribit(expiry_str: str, grace_period_days: int) -> bool:
    """Check if Deribit option is expired beyond grace period."""
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=grace_period_days)
    except (ValueError, AttributeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse Deribit expiry date '%s': %s", expiry_str, exc)
        return False
    else:
        return expiry_date < cutoff_time


def extract_expiration_time(market_data: dict) -> Optional[str]:
    """Extract expiration time string from market data."""
    expiration_time_raw = market_data.get(b"latest_expiration_time")
    if expiration_time_raw is None:
        expiration_time_raw = market_data.get("latest_expiration_time")
    if not expiration_time_raw:
        return None
    return expiration_time_raw.decode() if isinstance(expiration_time_raw, bytes) else str(expiration_time_raw)


# Constants
MIN_DERIBIT_KEY_PARTS = 5  # Minimum parts in deribit option key (markets:deribit:option:CURRENCY:EXPIRY:...)
_BATCH_SIZE = 200


def _extract_deribit_expiry(key_str: str) -> str | None:
    """Return the expiry portion of a Deribit key, or None if invalid/perpetual."""
    parts = key_str.split(":")
    if len(parts) < MIN_DERIBIT_KEY_PARTS:
        return None
    expiry_str = parts[4]
    if expiry_str.lower() == "perpetual":
        return None
    return expiry_str


class ExpiredMarketCleaner:
    """Clean up expired markets from Redis."""

    def __init__(self, redis_client: RedisClient, *, grace_period_days: int = 0) -> None:
        """Initialize cleaner."""
        self._redis = redis_client
        self._grace_period_days = grace_period_days

    async def cleanup_kalshi_markets(self) -> int:
        """Clean up expired Kalshi markets."""
        all_keys = await self._scan_kalshi_keys()
        if not all_keys:
            return 0

        deleted_count = 0
        for i in range(0, len(all_keys), _BATCH_SIZE):
            deleted_count += await self._delete_expired_kalshi_batch(all_keys[i : i + _BATCH_SIZE])

        if deleted_count > 0:
            logger.info("Cleaned up %d expired Kalshi markets", deleted_count)

        return deleted_count

    async def _scan_kalshi_keys(self) -> list[str]:
        """Scan and return all Kalshi market keys."""
        all_keys: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match="markets:kalshi:*", count=100))
            for key in keys:
                all_keys.append(key.decode() if isinstance(key, bytes) else str(key))
            if cursor == 0:
                break
        return all_keys

    async def _delete_expired_kalshi_batch(self, batch: list[str]) -> int:
        """Pipeline hgetall for a batch of keys and delete expired ones."""
        pipe = self._redis.pipeline()
        for key_str in batch:
            pipe.hgetall(key_str)
        results = await ensure_awaitable(pipe.execute())

        keys_to_delete = [
            key_str for key_str, market_data in zip(batch, results) if market_data and self._kalshi_market_is_expired(market_data)
        ]

        if keys_to_delete:
            del_pipe = self._redis.pipeline()
            for key_str in keys_to_delete:
                del_pipe.delete(key_str)
            await ensure_awaitable(del_pipe.execute())
            for key_str in keys_to_delete:
                logger.debug("Deleted expired Kalshi market: %s", key_str)

        return len(keys_to_delete)

    def _kalshi_market_is_expired(self, market_data: dict) -> bool:
        """Check whether a Kalshi market hash is expired."""
        expiration_time_str = extract_expiration_time(market_data)
        if not expiration_time_str:
            return False
        return is_expired_kalshi(expiration_time_str, self._grace_period_days)

    async def cleanup_deribit_options(self) -> int:
        """Clean up expired Deribit options."""
        return await self._cleanup_deribit_instruments("option")

    async def cleanup_deribit_futures(self) -> int:
        """Clean up expired Deribit futures (excludes perpetuals)."""
        return await self._cleanup_deribit_instruments("future")

    async def _cleanup_deribit_instruments(self, instrument_type: str) -> int:
        """Clean up expired Deribit instruments of the specified type."""
        keys_to_delete = await self._scan_expired_deribit_keys(instrument_type)
        if keys_to_delete:
            await self._delete_deribit_keys(keys_to_delete, instrument_type)
        return len(keys_to_delete)

    async def _scan_expired_deribit_keys(self, instrument_type: str) -> list[str]:
        """Scan and return expired Deribit instrument keys."""
        pattern = f"markets:deribit:{instrument_type}:*"
        expired: list[str] = []
        cursor = 0
        while True:
            cursor, keys = await ensure_awaitable(self._redis.scan(cursor, match=pattern, count=100))
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                expiry_str = _extract_deribit_expiry(key_str)
                if expiry_str and is_expired_deribit(expiry_str, self._grace_period_days):
                    expired.append(key_str)
            if cursor == 0:
                break
        return expired

    async def _delete_deribit_keys(self, keys_to_delete: list[str], instrument_type: str) -> None:
        """Pipeline-delete a list of Deribit keys and log the result."""
        pipe = self._redis.pipeline()
        for key_str in keys_to_delete:
            pipe.delete(key_str)
        await ensure_awaitable(pipe.execute())
        for key_str in keys_to_delete:
            logger.debug("Deleted expired Deribit %s: %s", instrument_type, key_str)
        logger.info("Cleaned up %d expired Deribit %ss", len(keys_to_delete), instrument_type)
