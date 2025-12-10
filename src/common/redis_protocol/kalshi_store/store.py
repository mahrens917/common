"""
Redis protocol for Kalshi market data - Ultra-slim Facade (<400 lines)

Delegates ALL operations to specialized coordinators and helper modules.
"""

import logging
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from ...config.redis_schema import get_schema_config
from ..weather_station_resolver import WeatherStationResolver
from .store_helpers.attribute_resolution import kalshi_store_getattr
from .store_helpers.property_management import setup_kalshi_store_properties
from .store_helpers.scanner import scan_market_keys
from .store_helpers.static_methods import setup_kalshi_store_static_methods
from .store_helpers.ticker_finder import find_currency_market_tickers
from .store_initializer import initialize_kalshi_store
from .store_methods import (
    get_active_strikes_and_expiries,
    get_interpolation_results,
    get_market_data_for_strike_expiry,
    get_markets_by_currency,
    is_market_expired,
)
from .utils_coercion import default_weather_station_loader as _canonical_weather_loader

SCHEMA = get_schema_config()
logger = logging.getLogger(__name__)
default_weather_station_loader = _canonical_weather_loader
_default_weather_station_loader = default_weather_station_loader


def _make_setter(attr_name: str):
    def _setter(self, value: Any) -> None:
        setattr(self, attr_name, value)

    return _setter


async def _get_redis_impl(store: "KalshiStore") -> Redis:
    ensure_redis = getattr(store, "_ensure_redis_connection")
    if not await ensure_redis():
        raise RuntimeError("Failed to ensure Redis connection")
    if store.redis is not None:
        return store.redis
    connection = getattr(store, "_connection")
    if connection is None:
        raise RuntimeError("Redis connection manager is undefined")
    return await connection.get_redis()


async def _ensure_redis_connection_impl(store: "KalshiStore") -> bool:
    connection = getattr(store, "_connection")
    if connection is None:
        return False
    return await connection.ensure_redis_connection()


async def _write_enhanced_market_data(store: "KalshiStore", market_ticker: str, field_updates: Dict[str, Any]) -> bool:
    ensure_redis = getattr(store, "_ensure_redis_connection")
    if not await ensure_redis():
        raise RuntimeError("Failed to ensure Redis connection for market write")

    writer = getattr(store, "_writer", None)
    if writer is None:
        raise RuntimeError("KalshiStore writer is not initialized")

    updater = getattr(writer, "_market_updater", None)
    if updater is not None:
        get_redis = getattr(store, "_get_redis")
        updater.redis = await get_redis()

    key_resolver = getattr(store, "get_market_key", None)
    if not callable(key_resolver):
        raise TypeError("KalshiStore helper missing get_market_key")

    market_key = key_resolver(market_ticker)
    return await writer.write_enhanced_market_data(market_ticker, market_key, field_updates)


async def _store_market_metadata(
    store: "KalshiStore",
    market_ticker: str,
    market_data: Dict[str, Any],
    *,
    event_data: Optional[Dict[str, Any]] = None,
    overwrite: bool = True,
) -> bool:
    ensure_redis = getattr(store, "_ensure_redis_connection")
    if not await ensure_redis():
        raise RuntimeError("Failed to ensure Redis connection for store_market_metadata")

    metadata_delegator = getattr(store, "_metadata_delegator", None)
    if metadata_delegator is not None:
        return await metadata_delegator.store_market_metadata(market_ticker, market_data, event_data=event_data, overwrite=overwrite)

    writer_delegator = getattr(store, "_writer", None)
    if writer_delegator is not None:
        return await writer_delegator.store_market_metadata(market_ticker, market_data, event_data=event_data, overwrite=overwrite)

    raise RuntimeError("KalshiStore is not initialized for metadata writes")


class KalshiStore:
    redis: Optional[Redis]
    service_prefix: Optional[str]
    logger: logging.Logger
    weather_resolver: WeatherStationResolver
    _connection: Optional[Any]
    _metadata: Optional[Any]
    _subscription: Optional[Any]
    _reader: Optional[Any]
    _writer: Optional[Any]
    _cleaner: Optional[Any]
    _orderbook: Optional[Any]
    _property_mgr: Optional[Any]
    _conn_delegator: Optional[Any]
    _metadata_delegator: Optional[Any]
    _subscription_delegator: Optional[Any]
    _query_delegator: Optional[Any]
    _write_delegator: Optional[Any]
    _orderbook_delegator: Optional[Any]
    _cleanup_delegator: Optional[Any]
    _utility_delegator: Optional[Any]
    _storage_delegator: Optional[Any]
    _attr_resolver: Optional[Any]

    def __init__(
        self,
        redis: Optional[Redis] = None,
        service_prefix: Optional[str] = None,
        *,
        weather_resolver: Optional[WeatherStationResolver] = None,
    ) -> None:
        initialize_kalshi_store(self, redis, service_prefix, weather_resolver)

    async def _get_redis(self) -> Redis:
        return await _get_redis_impl(self)

    async def _ensure_redis_connection(self) -> bool:
        return await _ensure_redis_connection_impl(self)

    async def _connect_with_retry(self, *, allow_reuse: bool, context: str, attempts: int = 3, retry_delay: float = 0.1) -> bool:
        if self._connection is None:
            raise AttributeError("Connection manager unavailable")
        if hasattr(self._connection, "_connect_with_retry"):
            return await self._connection._connect_with_retry(
                allow_reuse=allow_reuse, context=context, attempts=attempts, retry_delay=retry_delay
            )
        if hasattr(self._connection, "connect_with_retry"):
            return await self._connection.connect_with_retry(
                allow_reuse=allow_reuse, context=context, attempts=attempts, retry_delay=retry_delay
            )
        raise AttributeError("_connect_with_retry not supported by connection manager")

    async def _find_currency_market_tickers(self, currency: str) -> List[str]:
        return await find_currency_market_tickers(self, currency)

    async def _scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        return await scan_market_keys(self, patterns)

    async def get_markets_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        return await get_markets_by_currency(self, currency)

    async def get_active_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict]]:
        return await get_active_strikes_and_expiries(self, currency)

    async def get_interpolation_results(self, currency: str) -> Dict[str, Dict[str, Any]]:
        return await get_interpolation_results(self, currency)

    async def write_enhanced_market_data(self, market_ticker: str, field_updates: Dict[str, Any]) -> bool:
        return await _write_enhanced_market_data(self, market_ticker, field_updates)

    async def get_market_data_for_strike_expiry(self, currency: str, expiry_date: str, strike: float) -> Optional[Dict[str, Any]]:
        return await get_market_data_for_strike_expiry(self, currency, expiry_date, strike)

    async def is_market_expired(self, market_ticker: str) -> bool:
        return await is_market_expired(self, market_ticker)

    async def store_market_metadata(
        self, market_ticker: str, market_data: Dict[str, Any], *, event_data: Optional[Dict[str, Any]] = None, overwrite: bool = True
    ) -> bool:
        return await _store_market_metadata(self, market_ticker, market_data, event_data=event_data, overwrite=overwrite)

    def get_market_key(self, market_ticker: str) -> str:
        reader = getattr(self, "_reader", None)
        if reader is not None and hasattr(reader, "get_market_key"):
            return reader.get_market_key(market_ticker)
        attr_resolver = getattr(self, "_attr_resolver", None)
        if attr_resolver is not None:
            return attr_resolver.resolve("get_market_key")(market_ticker)
        raise NotImplementedError("KalshiStore helper not bound for get_market_key")

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)


_SETTABLE_ATTRIBUTES = {
    "connection": "_connection",
    "metadata": "_metadata",
    "subscription": "_subscription",
    "reader": "_reader",
    "writer": "_writer",
    "cleaner": "_cleaner",
    "orderbook": "_orderbook",
    "property_mgr": "_property_mgr",
    "conn_delegator": "_conn_delegator",
    "metadata_delegator": "_metadata_delegator",
    "subscription_delegator": "_subscription_delegator",
    "query_delegator": "_query_delegator",
    "write_delegator": "_write_delegator",
    "orderbook_delegator": "_orderbook_delegator",
    "cleanup_delegator": "_cleanup_delegator",
    "utility_delegator": "_utility_delegator",
    "storage_delegator": "_storage_delegator",
    "attr_resolver": "_attr_resolver",
}

for method_suffix, attr_name in _SETTABLE_ATTRIBUTES.items():
    setattr(KalshiStore, f"set_{method_suffix}", _make_setter(attr_name))

    # Setter helpers used during initialization (avoids direct private usage).

# Set up properties, getattr, and static methods
setup_kalshi_store_properties(KalshiStore)
setattr(KalshiStore, "__getattr__", kalshi_store_getattr)
setup_kalshi_store_static_methods(KalshiStore)
