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
from redis.exceptions import RedisError

from . import config
from .atomic_redis_operations_helpers.data_converter import DataConverter
from .atomic_redis_operations_helpers.data_fetcher import DataFetcher, RedisDataValidationError
from .atomic_redis_operations_helpers.deletion_validator import DeletionValidator
from .atomic_redis_operations_helpers.field_validator import FieldValidator
from .atomic_redis_operations_helpers.spread_validator import SpreadValidator
from .atomic_redis_operations_helpers.transaction_writer import TransactionWriter

logger = logging.getLogger(__name__)

# Retry configuration - drawn from real production requirements
MAX_READ_RETRIES = config.REDIS_MAX_RETRIES  # Use existing config value
READ_RETRY_DELAY_MS = int(config.REDIS_RETRY_DELAY * 1000)  # Convert to milliseconds
SPREAD_VALIDATION_ENABLED = True  # Enable bid/ask spread validation

__all__ = ["AtomicRedisOperations", "RedisDataValidationError"]

sys.modules.setdefault("common.redis_protocol.atomic_operations.asyncio", asyncio)

# Error types for atomic operations
_REDIS_ATOMIC_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
    RedisDataValidationError,
)


class AtomicRedisOperations:
    """
    Provides atomic Redis operations to prevent race conditions in market data.

    This class ensures that market data writes are atomic across all fields,
    and reads include validation to detect and retry on partial data.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize atomic operations with a Redis client.

        Args:
            redis_client: Redis connection with decode_responses=True
        """
        self.redis = redis_client
        self.logger = logger
        self._transaction_writer = TransactionWriter(redis_client)
        self._data_fetcher = DataFetcher(redis_client)
        self._field_validator = FieldValidator(MAX_READ_RETRIES)
        self._data_converter = DataConverter(MAX_READ_RETRIES)
        self._spread_validator = SpreadValidator(MAX_READ_RETRIES)
        self._deletion_validator = DeletionValidator(redis_client)

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
        return await self._transaction_writer.atomic_market_data_write(store_key, market_data)

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
        if not required_fields:
            required_fields = [
                "best_bid",
                "best_ask",
                "best_bid_size",
                "best_ask_size",
            ]
        last_error: Optional[Exception] = None

        for attempt in range(MAX_READ_RETRIES):
            try:
                raw_data = await self._data_fetcher.fetch_market_data(store_key)
                self._field_validator.ensure_required_fields(raw_data, required_fields, store_key, attempt)
                converted_data = self._data_converter.convert_market_payload(raw_data, store_key, attempt)
                self._spread_validator.validate_bid_ask_spread(converted_data, store_key, attempt)
                self.logger.debug("Safe read succeeded for key: %s", store_key)
            except RedisDataValidationError as exc:
                last_error = exc
                if attempt < MAX_READ_RETRIES - 1:
                    await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                    continue
                raise RedisDataValidationError(f"Error reading market data from key {store_key}") from exc
            except _REDIS_ATOMIC_ERRORS as exc:
                message = f"Error reading market data from key {store_key} ({type(exc).__name__})"
                self.logger.exception("%s, attempt %s/%s", message, attempt + 1, MAX_READ_RETRIES)
                last_error = exc if isinstance(exc, RedisDataValidationError) else RedisDataValidationError(message)
                if attempt < MAX_READ_RETRIES - 1:
                    await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                    continue
                raise RedisDataValidationError(message) from last_error
            else:
                return converted_data

        raise RedisDataValidationError(f"Error reading market data from key {store_key}") from last_error

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
        return await self._deletion_validator.atomic_delete_if_invalid(store_key, validation_data)
