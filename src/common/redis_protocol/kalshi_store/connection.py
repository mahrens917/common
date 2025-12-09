from __future__ import annotations

"""
Redis connection management for the KalshiStore.

This module owns everything related to establishing, validating, and
tearing down Redis clients so the main KalshiStore implementation can
focus on market logic.
"""

import logging
from typing import Optional

from redis.asyncio import Redis

from .connection_helpers import DelegatedProperty, PropertyManager
from .connection_helpers.dependencies_factory import (
    RedisConnectionDependencies,
    RedisConnectionDependenciesFactory,
)
from .connection_helpers.lifecycle_coordinator import LifecycleCoordinator
from .connection_helpers.retry_handler import ConnectionRetryConfig

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Slim coordinator for Redis lifecycle management."""

    redis = DelegatedProperty("redis")
    initialized = DelegatedProperty("initialized")
    pool = DelegatedProperty("pool")
    connection_settings = DelegatedProperty("connection_settings")
    connection_settings_logged = DelegatedProperty("connection_settings_logged")
    _METHOD_ADAPTER_PROXIED = {
        "resolve_connection_settings",
        "acquire_pool",
        "create_redis_client",
        "close_redis_client",
        "ping_connection",
        "verify_connection",
        "connect_with_retry",
        "reset_connection_state",
    }

    async def get_redis(self) -> Redis:
        return await self._lifecycle.get_redis()

    async def attach_redis_client(
        self, redis_client: Redis, *, health_check_timeout: float = 5.0
    ) -> None:
        await self._lifecycle.attach_redis_client(
            redis_client, health_check_timeout=health_check_timeout
        )

    def ensure_ready(self) -> None:
        self._lifecycle.ensure_ready()

    async def initialize(self) -> bool:
        return await self._lifecycle.initialize()

    async def close(self) -> None:
        await self._lifecycle.close()

    async def ensure_redis_connection(self) -> bool:
        return await self._lifecycle.ensure_redis_connection()

    async def ensure_connection(self) -> bool:
        return await self.ensure_redis_connection()

    def __getattr__(self, name: str):
        if name in self._METHOD_ADAPTER_PROXIED:
            return getattr(self._method_adapter, name)
        raise AttributeError(f"{self.__class__.__name__} has no attribute {name!r}")

    async def _connect_with_retry(
        self,
        *,
        allow_reuse: bool,
        context: str,
        attempts: int = 3,
        retry_delay: float = 0.1,
    ) -> bool:
        return await _connect_with_retry_impl(
            self,
            allow_reuse=allow_reuse,
            context=context,
            attempts=attempts,
            retry_delay=retry_delay,
        )

    def __init__(
        self,
        *,
        logger: logging.Logger,
        redis: Optional[Redis] = None,
        dependencies: Optional[RedisConnectionDependencies] = None,
    ) -> None:
        self._logger = logger
        self._redis: Optional[Redis] = redis
        self._pool = getattr(redis, "connection_pool", None) if redis else None
        self._initialized = redis is not None
        deps = dependencies or RedisConnectionDependenciesFactory.create(self, logger)
        self._property_manager = deps.property_manager
        self._properties = deps.property_accessor
        self._pool_manager = deps.pool_manager
        self._connection_verifier = deps.connection_verifier
        self._retry_handler = deps.retry_handler
        self._lifecycle: LifecycleCoordinator = deps.lifecycle
        self._method_adapter = deps.method_adapter

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def property_manager(self) -> PropertyManager:
        return self._property_manager


async def _connect_with_retry_impl(
    manager: "RedisConnectionManager",
    *,
    allow_reuse: bool,
    context: str,
    attempts: int = 3,
    retry_delay: float = 0.1,
) -> bool:
    pool_manager = getattr(manager, "_pool_manager")
    property_manager = getattr(manager, "_property_manager")
    connection_verifier = getattr(manager, "_connection_verifier")
    retry_handler = getattr(manager, "_retry_handler")

    async def pool_acquirer(*, allow_reuse: bool) -> Redis:
        return await pool_manager.acquire_pool(
            allow_reuse=allow_reuse,
            redis=property_manager.redis,
            close_callback=pool_manager.close_redis_client,
        )

    def on_success(redis_client: Redis) -> None:
        property_manager.redis = redis_client
        property_manager.pool = getattr(redis_client, "connection_pool", None)
        property_manager.initialized = True

    def on_failure() -> None:
        property_manager.redis = None
        property_manager.pool = None
        property_manager.initialized = False

    config = ConnectionRetryConfig(
        allow_reuse=allow_reuse,
        context=context,
        attempts=attempts,
        retry_delay=retry_delay,
        pool_acquirer=pool_acquirer,
        connection_verifier=connection_verifier.verify_connection,
        on_success=on_success,
        on_failure=on_failure,
        close_client=pool_manager.close_redis_client,
    )
    return await retry_handler.connect_with_retry(config)
