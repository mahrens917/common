"""
Deletion validator for Redis market data.

Validates market data and atomically deletes if invalid values are detected.
"""

import asyncio
import logging
from typing import Any, Dict

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..typing import ensure_awaitable

logger = logging.getLogger(__name__)

# Catch all atomic operation errors
REDIS_ATOMIC_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
)


class RedisDataValidationError(RuntimeError):
    """Raised when Redis market data cannot be validated after retries."""


class DeletionValidator:
    """Validates market data and deletes if invalid."""

    def __init__(self, redis_client: Redis):
        """
        Initialize deletion validator.

        Args:
            redis_client: Redis connection with decode_responses=True
        """
        self.redis = redis_client
        self.logger = logger

    async def atomic_delete_if_invalid(self, store_key: str, validation_data: Dict[str, Any]) -> bool:
        """
        Atomically delete a Redis key if the data contains invalid values.

        This is used when market data contains zero or None values that should
        result in the removal of the market data entry.

        Args:
            store_key: Redis key to potentially delete
            validation_data: Data to validate before deletion

        Returns:
            True if key was deleted, False if key was kept or didn't exist

        Raises:
            RedisDataValidationError: If validation or deletion fails
        """
        try:
            # Check if any critical values are zero or None
            critical_fields = ["best_bid", "best_ask", "best_bid_size", "best_ask_size"]

            for field in critical_fields:
                value = validation_data.get(field)
                if value is None or (isinstance(value, (int, float)) and value == 0):
                    # Invalid data detected, delete the key atomically
                    deleted_count = await ensure_awaitable(self.redis.delete(store_key))
                    if deleted_count > 0:
                        self.logger.debug(f"Deleted invalid market data for key: {store_key}")
                        return True
                    else:
                        self.logger.debug(f"Key {store_key} did not exist for deletion")
                        return False

            # Data is valid, don't delete

            else:
                return False
        except REDIS_ATOMIC_ERRORS as exc:
            self.logger.exception(
                "Error in atomic delete validation for key %s (%s): %s",
                store_key,
                type(exc).__name__,
            )
            raise RedisDataValidationError(f"Failed to validate market data for key {store_key}") from exc
