from __future__ import annotations

"""
Connection lifecycle coordination for RedisConnectionManager.

Handles initialization, health checks, and graceful shutdown.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class LifecycleCoordinator:
    """Manages connection initialization, health monitoring, and shutdown."""

    def __init__(self, manager: "RedisConnectionManager") -> None:
        self._manager = manager

    async def get_redis(self) -> Redis:
        if not await self.ensure_redis_connection():
            raise RuntimeError("Failed to establish Redis connection")
        assert self._manager.redis is not None, "Redis connection should be established"
        return self._manager.redis

    async def attach_redis_client(
        self, redis_client: Redis, *, health_check_timeout: float = 5.0
    ) -> None:
        from .connection_verifier import ConnectionVerifier

        verifier = ConnectionVerifier()
        await verifier.attach_redis_client(redis_client, health_check_timeout=health_check_timeout)
        self._manager.redis = redis_client
        self._manager.pool = getattr(redis_client, "connection_pool", None)
        self._manager.initialized = True

    def ensure_ready(self) -> None:
        if self._manager.redis is None:
            raise RuntimeError("KalshiStore has no Redis client attached")
        if not self._manager.initialized:
            raise RuntimeError("KalshiStore Redis client not initialised")

    async def initialize(self) -> bool:
        from .property_manager import PropertyManager

        property_manager = PropertyManager(self._manager)
        property_manager.settings_resolver.resolve_connection_settings()
        return await self._connect_with_retry(
            allow_reuse=False, context="initialize", attempts=3, retry_delay=0.5
        )

    async def close(self) -> None:
        if not self._manager.pool:
            self._manager.redis = None
            return
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                self._manager.pool = None
                self._manager.redis = None
                return
            from .pool_manager import PoolManager

            pool_manager = PoolManager()
            await pool_manager.cleanup_pool()
        finally:
            self._manager.pool = None
            self._manager.redis = None
            self._manager.initialized = False

    async def ensure_redis_connection(self) -> bool:
        return await self._connect_with_retry(
            allow_reuse=True, context="_ensure_redis_connection", attempts=3, retry_delay=0.1
        )

    async def _connect_with_retry(
        self,
        *,
        allow_reuse: bool,
        context: str,
        attempts: int = 3,
        retry_delay: float = 0.1,
    ) -> bool:
        from .connection_verifier import ConnectionVerifier
        from .method_adapter import MethodAdapter
        from .retry_handler import ConnectionRetryConfig, RetryHandler

        retry_handler = RetryHandler(self._manager.logger)
        connection_verifier = ConnectionVerifier()
        method_adapter = MethodAdapter(self._manager)

        def on_success(redis_client: Any) -> None:
            self._manager.redis = redis_client
            self._manager.pool = getattr(redis_client, "connection_pool", None)
            self._manager.initialized = True

        def on_failure() -> None:
            method_adapter.reset_connection_state()
            self._manager.redis = None
            self._manager.pool = None
            self._manager.initialized = False

        config = ConnectionRetryConfig(
            allow_reuse=allow_reuse,
            context=context,
            attempts=attempts,
            retry_delay=retry_delay,
            pool_acquirer=method_adapter.acquire_pool,
            connection_verifier=connection_verifier.verify_connection,
            on_success=on_success,
            on_failure=on_failure,
            close_client=method_adapter.close_redis_client,
        )
        return await retry_handler.connect_with_retry(config)
