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
from .close_positions_command import (
    CLOSE_POSITIONS_COMMAND_KEY,
    clear_close_positions_command,
    get_close_positions_command,
    request_close_all_positions,
)
from .connection import cleanup_redis_pool, get_redis_pool
from .connection_pool_core import get_retry_redis_client
from .converters import coerce_float, decode_redis_hash, decode_redis_value
from .kalshi_store import KalshiStore
from .market_normalization import ensure_market_metadata_fields
from .market_ownership import can_algo_own_market, can_algo_own_market_type, configure_ownership, get_required_owner
from .market_update_api import (
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
from .restart_service_command import (
    RESTART_SERVICE_COMMAND_KEY,
    RestartServiceResult,
    clear_restart_service_command,
    clear_restart_service_result,
    get_restart_service_command,
    get_restart_service_result,
    request_restart_service,
    write_restart_service_result,
)
from .retry_client import RetryPipeline, RetryRedisClient
from .subscription_store import SubscriptionStore
from .trading_toggle_api import (
    ALGO_TRADING_KEY_PREFIX,
    get_all_algo_trading_states,
    initialize_algo_trading_defaults,
    is_algo_trading_enabled,
    set_algo_trading_enabled,
    set_all_algo_trading_enabled,
    toggle_algo_trading,
)

__all__ = [
    "RetryPipeline",
    "RetryRedisClient",
    "can_algo_own_market",
    "can_algo_own_market_type",
    "configure_ownership",
    "get_redis_pool",
    "get_retry_redis_client",
    "get_required_owner",
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
    "ALGO_TRADING_KEY_PREFIX",
    "get_all_algo_trading_states",
    "initialize_algo_trading_defaults",
    "is_algo_trading_enabled",
    "set_algo_trading_enabled",
    "set_all_algo_trading_enabled",
    "toggle_algo_trading",
    "CLOSE_POSITIONS_COMMAND_KEY",
    "clear_close_positions_command",
    "get_close_positions_command",
    "request_close_all_positions",
    "RESTART_SERVICE_COMMAND_KEY",
    "RestartServiceResult",
    "clear_restart_service_command",
    "clear_restart_service_result",
    "get_restart_service_command",
    "get_restart_service_result",
    "request_restart_service",
    "write_restart_service_result",
    "ALGO_STATS_KEY_PREFIX",
    "AlgoStatsData",
    "increment_algo_stats",
    "read_algo_stats",
    "read_all_algo_stats",
    "reset_algo_stats",
    "write_algo_stats",
]
