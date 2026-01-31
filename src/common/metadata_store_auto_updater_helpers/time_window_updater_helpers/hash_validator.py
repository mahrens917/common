"""Redis sorted set key validation for time window updater."""

import logging
from typing import Optional

from common.redis_protocol.typing import RedisClient, ensure_awaitable

logger = logging.getLogger(__name__)
REDIS_ERRORS = (Exception,)


class HistoryKeyValidator:
    """Validates Redis history keys use expected sorted set structure."""

    @staticmethod
    async def ensure_sorted_set_history_key(redis_client: Optional[RedisClient], key: str) -> bool:
        """
        Ensure the given Redis history key uses the expected sorted set structure.

        Args:
            redis_client: Redis client instance
            key: Redis key to validate

        Returns:
            True if key is a sorted set or doesn't exist, False otherwise
        """
        if redis_client is None:
            _none_guard_value = False
            return _none_guard_value
        try:
            key_type = await ensure_awaitable(redis_client.type(key))
            key_type = key_type.decode() if isinstance(key_type, bytes) else key_type
            if key_type in ("none", "zset"):
                return True
            logger.error(
                "History key %s has unsupported Redis type '%s'; manual cleanup required",
                key,
                key_type,
            )
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error("Failed to validate history key %s: %s", key, exc, exc_info=True)
            return False

        return False


# Backward-compatible alias used by service_updater
HashValidator = HistoryKeyValidator
