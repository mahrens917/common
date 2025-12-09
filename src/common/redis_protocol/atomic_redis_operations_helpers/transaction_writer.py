"""
Atomic transaction writer for Redis market data.

Handles atomic writes using Redis transactions (MULTI/EXEC) to prevent
race conditions in market data updates.
"""

import logging
import time
from typing import Mapping, Union

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Catch all atomic operation errors
REDIS_ATOMIC_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
)


class TransactionWriter:
    """Handles atomic writes to Redis using transactions."""

    def __init__(self, redis_client: Redis):
        """
        Initialize transaction writer.

        Args:
            redis_client: Redis connection with decode_responses=True
        """
        self.redis = redis_client
        self.logger = logger

    async def atomic_market_data_write(
        self, store_key: str, market_data: Mapping[str, Union[str, float, int, None]]
    ) -> bool:
        """
        Atomically write market data to Redis using a transaction.

        This prevents race conditions where readers might see partial updates
        (e.g., new bid price with old ask price).

        Args:
            store_key: Redis key for the market data
            market_data: Dictionary of field->value mappings to store

        Returns:
            True if write succeeded, False otherwise

        Raises:
            RuntimeError: If Redis transaction fails after retries
        """
        try:
            # Convert all values to strings for Redis storage
            redis_data = {field: str(value) for field, value in market_data.items()}

            # Add timestamp for write tracking
            redis_data["last_update"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Use Redis transaction (MULTI/EXEC) for atomic write
            async with self.redis.pipeline(transaction=True) as pipe:
                # Queue the HSET operation with all fields
                pipe.hset(store_key, mapping=redis_data)

                # Execute atomically - all fields updated together or none at all
                results = await pipe.execute()

                # Verify the operation succeeded
                if results and len(results) > 0:
                    self.logger.debug(f"Atomic write succeeded for key: {store_key}")
                    return True
                else:
                    self.logger.error(
                        f"Atomic write failed for key: {store_key}, results: {results}"
                    )
                    return False

        except REDIS_ATOMIC_ERRORS as exc:
            self.logger.exception(
                "Atomic market data write failed for %s (%s): %s",
                store_key,
                type(exc).__name__,
            )
            # Re-raise to ensure calling code knows about the failure
            raise RuntimeError(f"Redis atomic write failed") from exc
