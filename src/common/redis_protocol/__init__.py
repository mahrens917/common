"""
Redis protocol package
"""

from .algo_stats_api import (
    ALGO_STATS_KEY_PREFIX,
    AlgoStatsData,
    increment_algo_stats,
    read_algo_stats,
    read_all_algo_stats,
    reset_algo_stats,
    write_algo_stats,
)
from .batching import BatchManager
from .connection import cleanup_redis_pool, get_redis_pool
from .converters import coerce_float, decode_redis_hash, decode_redis_value
from .kalshi_store import KalshiStore
from .market_normalization import ensure_market_metadata_fields
from .market_update_api import (
    VALID_ALGOS,
    MarketUpdateResult,
    clear_algo_ownership,
    get_market_algo,
    request_market_update,
)
from .messages import IndexMetadata, InstrumentMetadata, MarketData, SubscriptionUpdate
from .persistence_manager import (
    RedisPersistenceManager,
    ensure_redis_persistence,
    get_redis_persistence_status,
)
from .probability_store import ProbabilityStore
from .subscription_store import SubscriptionStore
from .trading_toggle_api import (
    TRADING_ENABLED_KEY,
    is_trading_enabled,
    set_trading_enabled,
    toggle_trading,
)

__all__ = [
    "get_redis_pool",
    "cleanup_redis_pool",
    "RedisPersistenceManager",
    "ensure_redis_persistence",
    "get_redis_persistence_status",
    "SubscriptionStore",
    "SubscriptionUpdate",
    "InstrumentMetadata",
    "IndexMetadata",
    "MarketData",
    "BatchManager",
    "KalshiStore",
    "ensure_market_metadata_fields",
    "ProbabilityStore",
    "decode_redis_value",
    "decode_redis_hash",
    "coerce_float",
    "request_market_update",
    "clear_algo_ownership",
    "get_market_algo",
    "MarketUpdateResult",
    "VALID_ALGOS",
    "TRADING_ENABLED_KEY",
    "is_trading_enabled",
    "set_trading_enabled",
    "toggle_trading",
    "ALGO_STATS_KEY_PREFIX",
    "AlgoStatsData",
    "increment_algo_stats",
    "read_algo_stats",
    "read_all_algo_stats",
    "reset_algo_stats",
    "write_algo_stats",
]
