"""
Redis writer for Kalshi market data

This module coordinates write operations for Kalshi market data in Redis,
delegating to specialized helper modules for different write operations.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from redis.asyncio import Redis

from ...redis_schema import KalshiMarketDescriptor, describe_kalshi_ticker
from .connection import RedisConnectionManager
from .metadata import KalshiMetadataAdapter
from .metadata_helpers.timestamp_normalization import normalize_timestamp as _normalize_timestamp
from .writer_helpers import ValidationWriter
from .writer_helpers.dependencies_factory import (
    KalshiMarketWriterDependencies,
    KalshiMarketWriterDependenciesFactory,
)

if TYPE_CHECKING:
    from .writer_helpers.batch_reader import BatchReader
    from .writer_helpers.batch_writer import BatchWriter
    from .writer_helpers.market_update_writer import MarketUpdateWriter
    from .writer_helpers.metadata_writer import MetadataWriter
    from .writer_helpers.orderbook_writer import OrderbookWriter
    from .writer_helpers.subscription_writer import SubscriptionWriter

logger = logging.getLogger(__name__)


class KalshiStoreError(RuntimeError):
    """Raised when KalshiStore operations cannot complete successfully."""


def _normalize_timestamp(value: Any) -> Any:
    return _normalize_timestamp(value)


class ValidationMixin:
    _validation: ValidationWriter

    async def _store_optional_field(self, redis: Redis, key: str, field: str, val: Optional[Any]) -> None:
        await self._validation.store_optional_field(key, field, val)

    async def store_optional_field(self, redis: Redis, key: str, field: str, val: Optional[Any]) -> None:
        await self._validation.store_optional_field(key, field, val)

    @staticmethod
    def _format_probability_value(value: Any) -> str:
        return ValidationWriter.format_probability_value(value)


class SubscriptionMixin:
    _subscription: "SubscriptionWriter"

    def _extract_weather_station_from_ticker(self, ticker: str) -> Optional[str]:
        return self._subscription.extract_weather_station_from_ticker(ticker)

    def derive_expiry_iso(self, ticker: str, meta: Dict[str, Any], desc: KalshiMarketDescriptor) -> str:
        return self._subscription.derive_expiry_iso(ticker, meta, desc)

    def ensure_market_metadata_fields(self, ticker: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        return self._subscription.ensure_market_metadata_fields(ticker, meta)


class MetadataWriterMixin:
    _metadata_writer: "MetadataWriter"
    _metadata: KalshiMetadataAdapter

    async def store_market_metadata(
        self,
        ticker: str,
        market_data: Dict[str, Any],
        *,
        event_data: Optional[Dict[str, Any]] = None,
        descriptor: Optional[KalshiMarketDescriptor] = None,
        overwrite: bool = True,
    ) -> bool:
        descriptor = descriptor or describe_kalshi_ticker(ticker)
        _ = overwrite
        weather_resolver = getattr(self._metadata, "weather_resolver", None)
        return await self._metadata_writer.store_market_metadata(
            ticker,
            market_data,
            event_data or market_data.get("event"),
            descriptor,
            weather_resolver,
        )


class MarketUpdaterMixin:
    _market_updater: "MarketUpdateWriter"

    async def write_enhanced_market_data(self, ticker: str, key: str, updates: Dict[str, Any]):
        return await self._market_updater.write_enhanced_market_data(ticker, key, updates)

    async def _update_trade_prices_for_market(self, ticker: str, bid: Optional[float], ask: Optional[float]):
        if bid is None or ask is None:
            return None
        await self._market_updater.update_trade_prices_for_market(ticker, bid, ask)

    async def update_trade_prices_for_market(self, ticker: str, bid: Optional[float], ask: Optional[float]) -> None:
        if bid is None or ask is None:
            return
        await self._market_updater.update_trade_prices_for_market(ticker, bid, ask)


class BatchMixin:
    _batch: "BatchWriter"
    _batch_reader: "BatchReader"

    async def update_interpolation_results(self, curr: str, results: Dict[str, Dict], key_func: Any):
        return await self._batch.update_interpolation_results(curr, results, key_func)

    async def get_interpolation_results(
        self,
        curr: str,
        keys: List[str],
        str_func: Any,
        int_func: Any,
        float_func: Any,
    ) -> Dict[str, Dict]:
        return await self._batch_reader.get_interpolation_results(curr, keys, str_func, int_func, float_func)


class OrderbookMixin:
    _orderbook: "OrderbookWriter"

    async def update_trade_tick(self, msg: Dict, key_func: Any, map_func: Any, str_func: Any):
        return await self._orderbook.update_trade_tick(msg, key_func, map_func, str_func)


class KalshiMarketWriter(
    ValidationMixin,
    SubscriptionMixin,
    MetadataWriterMixin,
    MarketUpdaterMixin,
    BatchMixin,
    OrderbookMixin,
):
    """Coordinates write operations for Kalshi market data in Redis."""

    def __init__(
        self,
        redis_connection: Redis,
        logger_instance: logging.Logger,
        connection_manager: RedisConnectionManager,
        metadata_adapter: KalshiMetadataAdapter,
        *,
        dependencies: Optional[KalshiMarketWriterDependencies] = None,
    ):
        self.redis = redis_connection
        self.logger = logger_instance
        self._connection = connection_manager
        self._metadata = metadata_adapter

        deps = dependencies or KalshiMarketWriterDependenciesFactory.create(
            redis_connection, logger_instance, metadata_adapter, connection_manager
        )
        self._validation = deps.validation
        self._metadata_writer = deps.metadata_writer
        self._market_updater = deps.market_updater
        self._orderbook = deps.orderbook
        self._batch = deps.batch
        self._batch_reader = deps.batch_reader
        self._subscription = deps.subscription
