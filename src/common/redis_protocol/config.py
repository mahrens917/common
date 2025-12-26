"""
Redis configuration and key definitions sourced from centralized settings.

Uses lazy loading to avoid requiring Redis env vars at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from common.config import env_float

# Type stubs for lazily-loaded variables (accessed via __getattr__)
if TYPE_CHECKING:
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None
    REDIS_SSL: bool
    REDIS_RETRY_ON_TIMEOUT: bool
    REDIS_SOCKET_TIMEOUT: float
    REDIS_SOCKET_CONNECT_TIMEOUT: float
    REDIS_HEALTH_CHECK_INTERVAL: float
    MARKET_KEY_PREFIX: str
    KALSHI_MARKET_PREFIX: str

DEFAULT_SOCKET_TIMEOUT_SECONDS = 10
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_HEALTH_CHECK_INTERVAL_SECONDS = 15

# Static constants that don't require env vars
UNIFIED_POOL_SIZE = 100
REDIS_CONNECTION_POOL_SIZE = 10
REDIS_CONNECTION_POOL_MAXSIZE = 20
REDIS_DNS_CACHE_TTL = 300
REDIS_DNS_CACHE_SIZE = 1000
PDF_SCAN_COUNT = 10000
PDF_BATCH_SIZE = 500
MARKET_BATCH_SIZE = 1000
MARKET_BATCH_TIME_MS = 10
MARKET_VERIFY_WRITES = False
REDIS_SOCKET_KEEPALIVE = True
REDIS_MAX_RETRIES = 3
REDIS_RETRY_DELAY = 0.1
REDIS_VERIFY_WRITES = True
DERIBIT_SUBSCRIPTION_KEY = "deribit:subscriptions"
KALSHI_SUBSCRIPTION_KEY = "kalshi:subscriptions"
MARKET_LATEST = "deribit_markets:latest"
DERIBIT_SUBSCRIPTION_CHANNEL = "deribit:subscription:updates"
KALSHI_SUBSCRIPTION_CHANNEL = "kalshi:subscription:updates"
PDF_CHANNEL = "pdf:updates"
PRICE_INDEX_CHANNEL = "price_index:updates"
API_TYPE_QUOTE = "quote"
API_TYPE_PRICE_INDEX = "deribit_price_index"
API_TYPE_VOLATILITY_INDEX = "deribit_volatility_index"
KALSHI_ORDERBOOK_PREFIX = "kalshi:orderbook:"
KALSHI_CHANNEL = "kalshi:updates"
HISTORY_KEY_PREFIX = "history:"
HISTORY_TTL_SECONDS = 86400


# Lazy-loaded values cache
_lazy_cache: dict[str, Any] = {}


def _normalize_optional_string(value: str | None) -> str | None:
    if value:
        return value
    return None


def _get_redis_settings() -> Any:
    """Lazily load Redis settings."""
    if "_redis_settings" not in _lazy_cache:
        from common.config.shared import get_redis_settings

        _lazy_cache["_redis_settings"] = get_redis_settings()
    return _lazy_cache["_redis_settings"]


def _get_schema() -> Any:
    """Lazily load schema config."""
    if "_schema" not in _lazy_cache:
        from common.config.redis_schema import get_schema_config

        _lazy_cache["_schema"] = get_schema_config()
    return _lazy_cache["_schema"]


def _get_socket_timeout() -> float:
    """Get socket timeout value."""
    settings = _get_redis_settings()
    configured = settings.socket_timeout if settings.socket_timeout is not None else DEFAULT_SOCKET_TIMEOUT_SECONDS
    return cast(float, env_float("REDIS_SOCKET_TIMEOUT", or_value=configured))


def _get_socket_connect_timeout() -> float:
    """Get socket connect timeout value."""
    settings = _get_redis_settings()
    configured = settings.socket_connect_timeout if settings.socket_connect_timeout is not None else DEFAULT_CONNECT_TIMEOUT_SECONDS
    return cast(float, env_float("REDIS_SOCKET_CONNECT_TIMEOUT", or_value=configured))


def _get_health_check_interval() -> float:
    """Get health check interval value."""
    settings = _get_redis_settings()
    configured = settings.health_check_interval if settings.health_check_interval is not None else DEFAULT_HEALTH_CHECK_INTERVAL_SECONDS
    return cast(float, env_float("REDIS_HEALTH_CHECK_INTERVAL", or_value=configured))


def _compute_lazy_value(name: str) -> Any:
    """Compute a lazy value by name."""
    settings = _get_redis_settings()
    schema = _get_schema()

    lazy_values = {
        "REDIS_HOST": settings.host,
        "REDIS_PORT": settings.port,
        "REDIS_DB": settings.db,
        "REDIS_PASSWORD": _normalize_optional_string(settings.password),
        "REDIS_SSL": bool(settings.ssl),
        "REDIS_RETRY_ON_TIMEOUT": settings.retry_on_timeout,
        "REDIS_SOCKET_TIMEOUT": _get_socket_timeout(),
        "REDIS_SOCKET_CONNECT_TIMEOUT": _get_socket_connect_timeout(),
        "REDIS_HEALTH_CHECK_INTERVAL": _get_health_check_interval(),
        "MARKET_KEY_PREFIX": f"{schema.deribit_market_prefix}:",
        "KALSHI_MARKET_PREFIX": f"{schema.kalshi_market_prefix}:",
    }

    if name in lazy_values:
        return lazy_values[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Names that require lazy loading
_LAZY_NAMES = frozenset(
    {
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_DB",
        "REDIS_PASSWORD",
        "REDIS_SSL",
        "REDIS_RETRY_ON_TIMEOUT",
        "REDIS_SOCKET_TIMEOUT",
        "REDIS_SOCKET_CONNECT_TIMEOUT",
        "REDIS_HEALTH_CHECK_INTERVAL",
        "MARKET_KEY_PREFIX",
        "KALSHI_MARKET_PREFIX",
    }
)


def __getattr__(name: str) -> Any:
    """Lazy load Redis-dependent configuration values."""
    if name in _LAZY_NAMES:
        if name not in _lazy_cache:
            _lazy_cache[name] = _compute_lazy_value(name)
        return _lazy_cache[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "API_TYPE_PRICE_INDEX",
    "API_TYPE_QUOTE",
    "API_TYPE_VOLATILITY_INDEX",
    "DERIBIT_SUBSCRIPTION_CHANNEL",
    "DERIBIT_SUBSCRIPTION_KEY",
    "HISTORY_KEY_PREFIX",
    "HISTORY_TTL_SECONDS",
    "KALSHI_CHANNEL",
    "KALSHI_MARKET_PREFIX",
    "KALSHI_ORDERBOOK_PREFIX",
    "KALSHI_SUBSCRIPTION_CHANNEL",
    "KALSHI_SUBSCRIPTION_KEY",
    "MARKET_BATCH_SIZE",
    "MARKET_BATCH_TIME_MS",
    "MARKET_KEY_PREFIX",
    "MARKET_LATEST",
    "MARKET_VERIFY_WRITES",
    "PDF_BATCH_SIZE",
    "PDF_CHANNEL",
    "PDF_SCAN_COUNT",
    "PRICE_INDEX_CHANNEL",
    "REDIS_CONNECTION_POOL_MAXSIZE",
    "REDIS_CONNECTION_POOL_SIZE",
    "REDIS_DB",
    "REDIS_PASSWORD",
    "REDIS_DNS_CACHE_SIZE",
    "REDIS_DNS_CACHE_TTL",
    "REDIS_HEALTH_CHECK_INTERVAL",
    "REDIS_HOST",
    "REDIS_MAX_RETRIES",
    "REDIS_PORT",
    "REDIS_RETRY_DELAY",
    "REDIS_RETRY_ON_TIMEOUT",
    "REDIS_SSL",
    "REDIS_SOCKET_CONNECT_TIMEOUT",
    "REDIS_SOCKET_KEEPALIVE",
    "REDIS_SOCKET_TIMEOUT",
    "REDIS_VERIFY_WRITES",
    "UNIFIED_POOL_SIZE",
]
