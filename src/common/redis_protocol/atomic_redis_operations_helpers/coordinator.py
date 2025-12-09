"""
Slim coordinator for atomic Redis operations.

Delegates all operations to focused helper components.
"""

import asyncio
import logging
from typing import Any, Dict, List, Mapping, Optional, Union

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .. import config
from .data_converter import DataConverter
from .data_fetcher import DataFetcher, RedisDataValidationError
from .deletion_validator import DeletionValidator
from .factory import AtomicOperationsFactory
from .field_validator import FieldValidator
from .spread_validator import SpreadValidator
from .transaction_writer import TransactionWriter

logger = logging.getLogger(__name__)

# Retry configuration
MAX_READ_RETRIES = config.REDIS_MAX_RETRIES
READ_RETRY_DELAY_MS = int(config.REDIS_RETRY_DELAY * 1000)

# Error types for atomic operations
REDIS_ATOMIC_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
    RedisDataValidationError,
)


class AtomicOperationsCoordinator:
    """Slim coordination layer for atomic Redis operations."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.logger = logger
        components = AtomicOperationsFactory.create_components(redis_client)
        self.transaction_writer: TransactionWriter = components["transaction_writer"]
        self.data_fetcher: DataFetcher = components["data_fetcher"]
        self.field_validator: FieldValidator = components["field_validator"]
        self.data_converter: DataConverter = components["data_converter"]
        self.spread_validator: SpreadValidator = components["spread_validator"]
        self.deletion_validator: DeletionValidator = components["deletion_validator"]

    async def atomic_market_data_write(
        self, store_key: str, market_data: Mapping[str, Union[str, float, int, None]]
    ) -> bool:
        return await self.transaction_writer.atomic_market_data_write(store_key, market_data)

    async def safe_market_data_read(
        self, store_key: str, required_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        required_fields = required_fields or [
            "best_bid",
            "best_ask",
            "best_bid_size",
            "best_ask_size",
        ]
        last_error: Optional[Exception] = None

        for attempt in range(MAX_READ_RETRIES):
            try:
                raw_data = await self.data_fetcher.fetch_market_data(store_key)
                self.field_validator.ensure_required_fields(
                    raw_data, required_fields, store_key, attempt
                )
                converted_data = self.data_converter.convert_market_payload(
                    raw_data, store_key, attempt
                )
                self.spread_validator.validate_bid_ask_spread(converted_data, store_key, attempt)
                self.logger.debug("Safe read succeeded for key: %s", store_key)
            except RedisDataValidationError as exc:
                last_error = exc
                if attempt < MAX_READ_RETRIES - 1:
                    await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                    continue
                raise
            except REDIS_ATOMIC_ERRORS as exc:
                message = f"Error reading market data from key {store_key} ({type(exc).__name__})"
                self.logger.exception("%s, attempt %s/%s")
                last_error = (
                    exc
                    if isinstance(exc, RedisDataValidationError)
                    else RedisDataValidationError(message)
                )
                if attempt < MAX_READ_RETRIES - 1:
                    await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                    continue
                raise RedisDataValidationError(message) from last_error
            else:
                return converted_data

        final_message = (
            f"Failed to read consistent data from key {store_key} after {MAX_READ_RETRIES} attempts"
        )
        self.logger.error(final_message)
        raise RedisDataValidationError(final_message) from last_error

    async def atomic_delete_if_invalid(
        self, store_key: str, validation_data: Dict[str, Any]
    ) -> bool:
        return await self.deletion_validator.atomic_delete_if_invalid(store_key, validation_data)


async def _atomic_market_data_write(
    self, store_key: str, market_data: Mapping[str, Union[str, float, int, None]]
) -> bool:
    return await self.transaction_writer.atomic_market_data_write(store_key, market_data)


async def _safe_market_data_read(
    self, store_key: str, required_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    required_fields = required_fields or [
        "best_bid",
        "best_ask",
        "best_bid_size",
        "best_ask_size",
    ]
    last_error: Optional[Exception] = None

    for attempt in range(MAX_READ_RETRIES):
        try:
            raw_data = await self.data_fetcher.fetch_market_data(store_key)
            self.field_validator.ensure_required_fields(
                raw_data, required_fields, store_key, attempt
            )
            converted_data = self.data_converter.convert_market_payload(
                raw_data, store_key, attempt
            )
            self.spread_validator.validate_bid_ask_spread(converted_data, store_key, attempt)
            self.logger.debug("Safe read succeeded for key: %s", store_key)
        except RedisDataValidationError as exc:
            last_error = exc
            if attempt < MAX_READ_RETRIES - 1:
                await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                continue
            raise
        except REDIS_ATOMIC_ERRORS as exc:
            message = f"Error reading market data from key {store_key} ({type(exc).__name__})"
            self.logger.exception("%s, attempt %s/%s")
            last_error = (
                exc
                if isinstance(exc, RedisDataValidationError)
                else RedisDataValidationError(message)
            )
            if attempt < MAX_READ_RETRIES - 1:
                await asyncio.sleep(READ_RETRY_DELAY_MS / 1000.0)
                continue
            raise RedisDataValidationError(message) from last_error
        else:
            return converted_data

    final_message = (
        f"Failed to read consistent data from key {store_key} after {MAX_READ_RETRIES} attempts"
    )
    self.logger.error(final_message)
    raise RedisDataValidationError(final_message) from last_error


async def _atomic_delete_if_invalid(self, store_key: str, validation_data: Dict[str, Any]) -> bool:
    return await self.deletion_validator.atomic_delete_if_invalid(store_key, validation_data)


setattr(AtomicOperationsCoordinator, "atomic_market_data_write", _atomic_market_data_write)
setattr(AtomicOperationsCoordinator, "safe_market_data_read", _safe_market_data_read)
setattr(AtomicOperationsCoordinator, "atomic_delete_if_invalid", _atomic_delete_if_invalid)
