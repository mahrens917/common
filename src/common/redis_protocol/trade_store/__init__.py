"""
Trade store package.

Expose the public TradeStore API while keeping internal modules private.
"""

from .store import OrderMetadataError, TradeStore, TradeStoreError, TradeStoreShutdownError

__all__ = [
    "TradeStore",
    "OrderMetadataError",
    "TradeStoreError",
    "TradeStoreShutdownError",
    "cleanup_redis_pool",
    "get_redis_pool",
    "Redis",
]
from redis.asyncio import Redis

from .. import cleanup_redis_pool, get_redis_pool
