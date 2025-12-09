"""Slim coordinator for TradeStore connection management."""

import logging
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from ...kalshi_store.connection import RedisConnectionManager
from .connection_manager_helpers import (
    ConnectionAcquisitionHelper,
    ConnectionRetryHelper,
    ConnectionSettingsHelper,
    ConnectionStateHelper,
    ConnectionVerificationHelper,
)


class TradeStoreConnectionManager:
    """Slim coordinator for Redis connection lifecycle in TradeStore."""

    def __init__(self, logger: logging.Logger, connection_manager: RedisConnectionManager):
        self.logger = logger
        self._connection = connection_manager
        self._acquisition = ConnectionAcquisitionHelper(logger, connection_manager)
        self._retry = ConnectionRetryHelper(logger, connection_manager)
        self._settings = ConnectionSettingsHelper(logger, connection_manager)
        self._state = ConnectionStateHelper(logger, connection_manager)
        self._verification = ConnectionVerificationHelper(logger, connection_manager)
        self._default_pool_acquirer = None

    def ensure_connection_manager(self) -> None:
        self._state.ensure_connection_manager()

    async def get_redis(self, redis_property_getter) -> Redis:
        return await self._acquisition.get_redis(
            redis_property_getter, self.ensure_redis_connection, self.ping_connection
        )

    async def ensure_redis_connection(self) -> bool:
        pool_acquirer = self._default_pool_acquirer
        return await self.connect_with_retry(
            allow_reuse=True,
            context="_ensure_redis_connection",
            attempts=3,
            retry_delay=0.1,
            pool_acquirer=pool_acquirer,
        )

    async def initialize(self, redis_setter, settings_resolver, pool_acquirer) -> bool:
        settings_resolver()
        self._default_pool_acquirer = pool_acquirer
        success = await self.connect_with_retry(
            allow_reuse=False,
            context="initialize",
            attempts=3,
            retry_delay=0.5,
            redis_setter=redis_setter,
            pool_acquirer=pool_acquirer,
        )
        if success:
            self.logger.info("TradeStore Redis connection successfully established and initialized")
        else:
            self.logger.error("Failed to establish Redis connection during TradeStore initialise()")
        return success

    async def close(self, redis_setter) -> None:
        await self._state.close(redis_setter)

    async def connect_with_retry(
        self,
        *,
        allow_reuse: bool,
        context: str,
        attempts: int = 3,
        retry_delay: float = 0.1,
        redis_setter=None,
        pool_acquirer=None,
    ) -> bool:
        from .connection_manager_helpers.retry import TradeStoreConnectionRetryConfig

        self.ensure_connection_manager()
        config = TradeStoreConnectionRetryConfig(
            allow_reuse=allow_reuse,
            context=context,
            attempts=attempts,
            retry_delay=retry_delay,
            pool_acquirer=pool_acquirer,
            verify_func=self.verify_connection,
            close_func=self.close_redis_client,
            reset_func=self.reset_connection_state,
            redis_setter=redis_setter,
        )
        return await self._retry.connect_with_retry(config)

    def resolve_connection_settings(self) -> Dict[str, Any]:
        return self._settings.resolve_connection_settings()

    async def verify_connection(self, redis: Any) -> tuple[bool, bool]:
        return await self._verification.verify_connection(redis)

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> tuple[bool, bool]:
        return await self._verification.ping_connection(redis, timeout=timeout)

    def reset_connection_state(self) -> None:
        self._state.reset_connection_state()

    async def close_redis_client(self, redis_client: Any, redis_setter=None) -> None:
        await self._state.close_redis_client(redis_client, redis_setter)

    @property
    def redis(self) -> Optional[Redis]:
        return self._state.redis

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        self._state.redis = value
