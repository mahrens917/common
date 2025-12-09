"""Connection operation factory for ConnectionRetryHelper."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from redis.asyncio import Redis

from .....kalshi_store.connection import RedisConnectionManager
from .....retry import RedisFatalError
from ....errors import TradeStoreError


@dataclass(frozen=True)
class ConnectionOperationConfig:
    """Configuration for creating connection operation."""

    connection_manager: RedisConnectionManager
    pool_acquirer: Optional[Callable]
    verify_func: Callable
    close_func: Callable
    reset_func: Callable
    redis_setter: Optional[Callable]
    context: str
    attempts: int
    allow_reuse: bool
    logger: logging.Logger


def create_connection_operation(config: ConnectionOperationConfig) -> Callable:
    """Create connection operation function."""

    async def _operation(attempt: int) -> Redis:
        if config.pool_acquirer:
            redis_client = await config.pool_acquirer(allow_reuse=config.allow_reuse)
        else:
            raise RuntimeError("pool_acquirer required for connect_with_retry")

        config.logger.debug(
            "%s: verifying Redis connection (attempt %s/%s)",
            config.context,
            attempt,
            config.attempts,
        )

        ok, fatal = await config.verify_func(redis_client)
        if ok:
            config.connection_manager.initialized = True
            config.logger.debug("%s: Redis connection established", config.context)
            return redis_client

        await config.close_func(redis_client, config.redis_setter)
        config.reset_func()

        if fatal:
            raise RedisFatalError("event loop shutting down during Redis ping")

        raise TradeStoreError("Redis connection failed health check")

    return _operation
