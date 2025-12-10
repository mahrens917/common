"""
Redis configuration and key definitions sourced from centralized settings.
"""

from common.config import env_float
from common.config.redis_schema import get_schema_config
from common.config.shared import get_redis_settings

_redis_settings = get_redis_settings()
_schema = get_schema_config()


DEFAULT_SOCKET_TIMEOUT_SECONDS = 10
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_HEALTH_CHECK_INTERVAL_SECONDS = 15


def _normalize_optional_string(value: str | None) -> str | None:
    if value:
        return value
    return None


# Redis connection settings pulled from shared configuration
REDIS_HOST: str = _redis_settings.host
REDIS_PORT: int = _redis_settings.port
REDIS_DB: int = _redis_settings.db
REDIS_PASSWORD: str | None = _normalize_optional_string(_redis_settings.password)
REDIS_SSL: bool = bool(_redis_settings.ssl)

# Unified connection pooling settings - single pool for all operations
UNIFIED_POOL_SIZE = 100  # Unified pool size for all Redis operations
REDIS_CONNECTION_POOL_SIZE = 10  # HTTP-style connection pool size
REDIS_CONNECTION_POOL_MAXSIZE = 20  # Maximum pool size
REDIS_DNS_CACHE_TTL = 300  # DNS cache TTL in seconds (5 minutes)
REDIS_DNS_CACHE_SIZE = 1000  # Maximum DNS cache entries

# Application-specific settings
PDF_SCAN_COUNT = 10000  # Much larger scan count for more efficient key retrieval
PDF_BATCH_SIZE = 500  # Increased batch size for processing instruments

# Market Collector settings
MARKET_BATCH_SIZE = 1000  # Larger batches for maximum throughput
MARKET_BATCH_TIME_MS = 10  # Process batches more frequently
MARKET_VERIFY_WRITES = False  # Skip verification for performance

# Common Redis settings with optional environment overrides
if _redis_settings.socket_timeout is not None:
    _DEFAULT_SOCKET_TIMEOUT = _redis_settings.socket_timeout
else:
    _DEFAULT_SOCKET_TIMEOUT = DEFAULT_SOCKET_TIMEOUT_SECONDS
if _redis_settings.socket_connect_timeout is not None:
    _DEFAULT_CONNECT_TIMEOUT = _redis_settings.socket_connect_timeout
else:
    _DEFAULT_CONNECT_TIMEOUT = DEFAULT_CONNECT_TIMEOUT_SECONDS
if _redis_settings.health_check_interval is not None:
    _DEFAULT_HEALTH_CHECK = _redis_settings.health_check_interval
else:
    _DEFAULT_HEALTH_CHECK = DEFAULT_HEALTH_CHECK_INTERVAL_SECONDS

REDIS_SOCKET_TIMEOUT = env_float("REDIS_SOCKET_TIMEOUT", or_value=_DEFAULT_SOCKET_TIMEOUT)
REDIS_SOCKET_CONNECT_TIMEOUT = env_float(
    "REDIS_SOCKET_CONNECT_TIMEOUT", or_value=_DEFAULT_CONNECT_TIMEOUT
)
REDIS_SOCKET_KEEPALIVE = True  # Enable TCP keepalive
REDIS_RETRY_ON_TIMEOUT = _redis_settings.retry_on_timeout
REDIS_HEALTH_CHECK_INTERVAL = env_float(
    "REDIS_HEALTH_CHECK_INTERVAL", or_value=_DEFAULT_HEALTH_CHECK
)
REDIS_MAX_RETRIES = 3  # Maximum number of retries for operations
REDIS_RETRY_DELAY = 0.1  # Initial retry delay in seconds
REDIS_VERIFY_WRITES = True  # Default write verification setting

# Simplified unified key patterns
MARKET_KEY_PREFIX = f"{_schema.deribit_market_prefix}:"

# Unified subscription storage
DERIBIT_SUBSCRIPTION_KEY = "deribit:subscriptions"
KALSHI_SUBSCRIPTION_KEY = "kalshi:subscriptions"

# Other keys
MARKET_LATEST = "deribit_markets:latest"

# Service-specific subscription channels
DERIBIT_SUBSCRIPTION_CHANNEL = "deribit:subscription:updates"  # For deribit subscription changes
KALSHI_SUBSCRIPTION_CHANNEL = "kalshi:subscription:updates"  # For kalshi subscription changes

# Other channels
PDF_CHANNEL = "pdf:updates"  # For PDF updates
PRICE_INDEX_CHANNEL = "price_index:updates"  # For price index updates

# API Types
API_TYPE_QUOTE = "quote"
API_TYPE_PRICE_INDEX = "deribit_price_index"
API_TYPE_VOLATILITY_INDEX = "deribit_volatility_index"

# Kalshi-specific keys and settings
KALSHI_MARKET_PREFIX = f"{_schema.kalshi_market_prefix}:"
KALSHI_ORDERBOOK_PREFIX = "kalshi:orderbook:"
KALSHI_CHANNEL = "kalshi:updates"

# History tracking settings (renamed from load tracking)
HISTORY_KEY_PREFIX = "history:"
HISTORY_TTL_SECONDS = 86400  # 24 hours TTL for history data

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
