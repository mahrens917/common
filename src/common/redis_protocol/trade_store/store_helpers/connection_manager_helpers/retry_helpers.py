"""Helper functions for ConnectionRetryHelper."""

import logging
from dataclasses import dataclass
from typing import Any, Callable

from ....retry import RedisFatalError
from ...errors import TradeStoreError


@dataclass(frozen=True)
class ConnectionOperationExecutor:
    """Configuration for executing connection operations."""

    redis_client: Any
    verify_func: Callable
    close_func: Callable
    reset_func: Callable
    redis_setter: Any
    context: str
    connection: Any
    logger: logging.Logger


async def execute_connection_operation(executor: ConnectionOperationExecutor):
    """Execute connection verification and handle errors."""
    ok, fatal = await executor.verify_func(executor.redis_client)
    if ok:
        executor.connection.initialized = True
        executor.logger.debug("%s: Redis connection established", executor.context)
        return executor.redis_client

    await executor.close_func(executor.redis_client, executor.redis_setter)
    executor.reset_func()

    if fatal:
        raise RedisFatalError("event loop shutting down during Redis ping")

    raise TradeStoreError("Redis connection failed health check")
