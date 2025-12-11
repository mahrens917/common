"""
Atomic Redis operations to prevent race conditions in market data writes/reads

This module provides atomic operations for Redis to ensure data consistency
when multiple processes are reading and writing market data at high frequency.

Key Features:
- Atomic multi-field hash updates using Redis transactions
- Safe read operations with retry logic and data validation
- Spread validation to detect partial writes
- Configurable retry parameters from environment

Note: Implementation delegated to coordinator for maintainability.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Mapping, Optional, Union

from redis.asyncio import Redis

from . import config
from .atomic_redis_operations_helpers.coordinator import AtomicOperationsCoordinator
from .atomic_redis_operations_helpers.data_fetcher import RedisDataValidationError

logger = logging.getLogger(__name__)

# Retry configuration - drawn from real production requirements
MAX_READ_RETRIES = config.REDIS_MAX_RETRIES  # Use existing config value
READ_RETRY_DELAY_MS = int(config.REDIS_RETRY_DELAY * 1000)  # Convert to milliseconds
SPREAD_VALIDATION_ENABLED = True  # Enable bid/ask spread validation

__all__ = ["AtomicRedisOperations", "RedisDataValidationError"]

sys.modules.setdefault("common.redis_protocol.atomic_operations.asyncio", asyncio)


class AtomicRedisOperations:
    """
    Provides atomic Redis operations to prevent race conditions in market data.

    This class ensures that market data writes are atomic across all fields,
    and reads include validation to detect and retry on partial data.

    Implementation Note: This class delegates all operations to a coordinator
    for better maintainability while preserving the public API.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize atomic operations with a Redis client.

        Args:
            redis_client: Redis connection with decode_responses=True
        """
        self.redis = redis_client
        self.logger = logger
        self._coordinator = AtomicOperationsCoordinator(redis_client)

    async def atomic_market_data_write(self, store_key: str, market_data: Mapping[str, Union[str, float, int, None]]) -> bool:
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
        return await self._coordinator.atomic_market_data_write(store_key, market_data)

    async def safe_market_data_read(self, store_key: str, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Safely read market data with retry logic and validation.

        This function detects partial writes and retries to ensure consistent data.
        It validates that all required fields are present and that bid/ask spreads
        are valid (bid <= ask).

        Args:
            store_key: Redis key to read from
            required_fields: List of required fields (defaults to standard market data fields)

        Returns:
            Dictionary of validated market data.

        Raises:
            RedisDataValidationError: If the data cannot be validated after retries.
        """
        return await self._coordinator.safe_market_data_read(store_key, required_fields)

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
        return await self._coordinator.atomic_delete_if_invalid(store_key, validation_data)
