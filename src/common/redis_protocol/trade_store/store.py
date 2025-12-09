"""
Redis protocol for Kalshi trade data storage and retrieval.

The TradeStore now composes dedicated components for persistence, aggregation,
metadata, and pricing concerns. The orchestration layer focuses on connection
management and fail-fast wiring, keeping each responsibility discoverable.
"""

import logging
from typing import Optional

from redis.asyncio import Redis

from ..typing import RedisClient
from .dependencies_factory import TradeStoreDependencies, TradeStoreDependenciesFactory
from .errors import OrderMetadataError, TradeStoreError, TradeStoreShutdownError

ORIGINAL_REDIS_CLASS = Redis

logger = logging.getLogger(__name__)


class TradeStore:
    """
    Redis-backed store for Kalshi trade data.

    TradeStore composes several internal services so each domain surface can be
    exercised independently whilst sharing the same Redis connection manager.
    """

    def __init__(
        self,
        redis: Optional[RedisClient] = None,
        *,
        dependencies: Optional[TradeStoreDependencies] = None,
    ) -> None:
        self.logger = logger
        deps = dependencies or TradeStoreDependenciesFactory.create(
            self.logger, redis, self._get_redis
        )
        self._base_connection = deps.base_connection
        self._connection_mgr = deps.connection_mgr
        self._pool_acquirer = deps.pool_acquirer
        self._executor = deps.executor
        self._deps = deps.deps
        self.timezone = deps.timezone
        self._keys = deps.keys
        self._codec = deps.codec
        self._repository = deps.repository
        self._metadata_store = deps.metadata_store
        self._queries = deps.queries
        self._pnl = deps.pnl
        self._price_updater = deps.price_updater
        self._api = deps.api

    async def _get_redis(self) -> RedisClient:
        """Get Redis client with automatic reconnection."""
        return await self._connection_mgr.get_redis(lambda: self.redis)

    async def initialize(self) -> bool:
        """Initialize Redis connection."""

        async def _acquire_pool(allow_reuse: bool):
            return await self._pool_acquirer.acquire_pool(
                allow_reuse=allow_reuse,
                redis_getter=lambda: self.redis,
                redis_setter=lambda v: setattr(self, "_redis_client", v),
                original_redis_class=ORIGINAL_REDIS_CLASS,
            )

        return await self._connection_mgr.initialize(
            redis_setter=lambda v: setattr(self, "_redis_client", v),
            settings_resolver=self._connection_mgr.resolve_connection_settings,
            pool_acquirer=_acquire_pool,
        )

    async def close(self) -> None:
        """Close Redis connection cleanly."""
        await self._connection_mgr.close(redis_setter=lambda v: setattr(self, "_redis_client", v))

    @property
    def redis(self) -> Optional[Redis]:
        """Get current Redis client."""
        return getattr(self, "_redis_client", self._connection_mgr.redis)

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        """Set Redis client."""
        self._redis_client = value
        self._connection_mgr.redis = value

    def __getattr__(self, name: str):
        """Delegate all other methods to API handler."""
        if hasattr(self._api, name):
            return getattr(self._api, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


__all__ = ["TradeStore", "OrderMetadataError", "TradeStoreError", "TradeStoreShutdownError"]
