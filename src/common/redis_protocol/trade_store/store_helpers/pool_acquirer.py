"""Redis pool acquisition for TradeStore."""

import importlib

from redis.asyncio import Redis

from ... import get_redis_pool
from ..errors import TradeStoreError


class PoolAcquirer:
    """Acquire and manage Redis connection pools."""

    def __init__(self, logger, connection_manager):
        self.logger = logger
        self.connection_manager = connection_manager

    async def acquire_pool(self, *, allow_reuse: bool, redis_getter, redis_setter, original_redis_class) -> Redis:
        """
        Acquire Redis connection pool.

        Args:
            allow_reuse: Whether to reuse existing connection
            redis_getter: Callable to get current redis property
            redis_setter: Callable to set redis property
            original_redis_class: Original Redis class for comparison

        Returns:
            Redis client with connection pool

        Raises:
            TradeStoreError: If pool acquisition fails
        """
        self.connection_manager.resolve_connection_settings()

        if allow_reuse and redis_getter() is not None:
            self.logger.debug("Reusing existing Redis connection")
            return redis_getter()

        if redis_getter() is not None:
            await self.connection_manager.close_redis_client(redis_getter())
            self.connection_manager.reset_connection_state()

        module = importlib.import_module("common.redis_protocol.trade_store")
        pool_getter = getattr(module, "get_redis_pool", get_redis_pool)
        pool = await pool_getter()

        if pool is None:
            raise TradeStoreError("get_redis_pool() returned None - check Redis configuration in ~/.env")

        redis_async = importlib.import_module("redis.asyncio")
        base_redis_cls = getattr(redis_async, "Redis")
        module_cls = getattr(module, "Redis", None)

        redis_cls = module_cls if module_cls is not None and module_cls is not original_redis_class else base_redis_cls

        client = redis_cls(connection_pool=pool, decode_responses=True)
        if client is None:
            raise TradeStoreError("Redis client creation failed")

        self.connection_manager._connection.pool = pool
        redis_setter(client)
        return client
