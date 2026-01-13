"""
Store initialization logic extracted from store.py.

This module contains the initialization and setup functions for KalshiStore.
"""

import logging
from typing import TYPE_CHECKING, Optional

from redis.asyncio import Redis

if TYPE_CHECKING:
    from .store import KalshiStore
    from .store_initializer_helpers.delegator_factory import DelegatorSet

from ...config.redis_schema import get_schema_config
from ..weather_station_resolver import WeatherStationResolver
from .connection import RedisConnectionManager
from .initialization_helpers import build_weather_resolver
from .orderbook import KalshiOrderbookProcessor
from .utils_coercion import default_weather_station_loader

SCHEMA = get_schema_config()
logger = logging.getLogger(__name__)


class KalshiStoreError(RuntimeError):
    """Raised when KalshiStore operations cannot complete successfully."""


def initialize_kalshi_store(
    store: "KalshiStore",
    redis: Optional[Redis],
    service_prefix: Optional[str],
    weather_resolver: Optional[WeatherStationResolver],
) -> None:
    from . import store as store_module
    from .store_initializer_helpers import create_core_components, create_delegators

    _ensure_valid_service_prefix(service_prefix)
    _assign_base_store_attributes(store, service_prefix, store_module, weather_resolver)

    connection, metadata, subscription, reader, writer, cleaner, _ = create_core_components(
        redis, service_prefix, store.logger, store.weather_resolver
    )

    _apply_core_components(store, connection, metadata, subscription, reader, writer, cleaner)

    orderbook_processor = _build_orderbook_processor(connection, store)
    store.set_orderbook(orderbook_processor)

    delegators, attr_resolver = create_delegators(
        connection,
        writer,
        reader,
        subscription,
        orderbook_processor,
        cleaner,
        lambda: store.weather_resolver,
    )

    _apply_delegators(store, delegators)
    store.set_attr_resolver(attr_resolver)


def _ensure_valid_service_prefix(service_prefix: Optional[str]) -> None:
    if service_prefix not in (None, "rest", "ws"):
        raise TypeError("service_prefix must be 'rest' or 'ws' when provided")


def _assign_base_store_attributes(
    store: "KalshiStore",
    service_prefix: Optional[str],
    store_module: object,
    weather_resolver: Optional[WeatherStationResolver],
) -> None:
    object.__setattr__(store, "service_prefix", service_prefix)
    object.__setattr__(store, "logger", logger)
    weather_loader = getattr(
        store_module,
        "_default_weather_station_loader",
        getattr(store_module, "default_weather_station_loader", default_weather_station_loader),
    )
    object.__setattr__(
        store,
        "weather_resolver",
        weather_resolver or build_weather_resolver(weather_loader, logger),
    )


def _apply_core_components(
    store: "KalshiStore",
    connection: RedisConnectionManager,
    metadata: object,
    subscription: object,
    reader: object,
    writer: object,
    cleaner: object,
) -> None:
    store.set_connection(connection)
    store.set_metadata(metadata)
    store.set_subscription(subscription)
    store.set_reader(reader)
    store.set_writer(writer)
    store.set_cleaner(cleaner)


def _build_trade_price_callback(store: "KalshiStore"):
    async def _dynamic_update_trade_prices(ticker: str, bid: Optional[float], ask: Optional[float]):
        """Wrapper that looks up the current _update_trade_prices_for_market method."""
        callback = getattr(store, "_update_trade_prices_for_market", None)
        if callback:
            await callback(ticker, bid, ask)

    return _dynamic_update_trade_prices


def _apply_delegators(store: "KalshiStore", delegators: "DelegatorSet") -> None:
    store.set_property_mgr(delegators.property_mgr)
    store.set_conn_delegator(delegators.conn_delegator)
    store.set_metadata_delegator(delegators.metadata_delegator)
    store.set_subscription_delegator(delegators.subscription_delegator)
    store.set_query_delegator(delegators.query_delegator)
    store.set_write_delegator(delegators.write_delegator)
    store.set_orderbook_delegator(delegators.orderbook_delegator)
    store.set_cleanup_delegator(delegators.cleanup_delegator)
    store.set_utility_delegator(delegators.utility_delegator)
    store.set_storage_delegator(delegators.storage_delegator)


def _build_orderbook_processor(connection: RedisConnectionManager, store: "KalshiStore") -> KalshiOrderbookProcessor:
    """Construct the KalshiOrderbookProcessor used by the store."""
    return KalshiOrderbookProcessor(
        redis_connection_manager=connection,
        logger_instance=store.logger,
        update_trade_prices_callback=_build_trade_price_callback(store),
    )
