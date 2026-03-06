"""Connection retry logic for TradeStore."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from redis.asyncio import Redis

from ....kalshi_store.connection import RedisConnectionManager
from ....retry import (
    RedisFatalError,
    RedisRetryContext,
    RedisRetryError,
    RedisRetryPolicy,
    execute_with_retry,
)
from ...errors import TradeStoreError
from .base import ConnectionHelperBase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeStoreConnectionRetryConfig:
    """Configuration for TradeStore Redis connection retry operations."""

    allow_reuse: bool
    context: str
    attempts: int
    retry_delay: float
    pool_acquirer: Optional[Callable]
    verify_func: Callable
    close_func: Callable
    reset_func: Callable
    redis_setter: Optional[Callable] = None


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


class ConnectionRetryHelper(ConnectionHelperBase):
    """Handle Redis connection retry operations."""

    async def connect_with_retry(self, config: TradeStoreConnectionRetryConfig) -> bool:
        """
        Attempt Redis connection with retry logic.

        Args:
            config: Configuration for connection retry operations

        Returns:
            True if connection succeeded
        """
        policy = _build_retry_policy(config.attempts, config.retry_delay)
        operation = _create_connection_operation_from_retry(helper=self, retry_config=config)
        on_retry = _create_retry_callback(config.context, self.logger)

        try:
            await execute_with_retry(
                operation,
                policy=policy,
                logger=self.logger,
                context=config.context,
                on_retry=on_retry,
            )
        except RedisFatalError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.debug("Expected exception, returning default value")
            return False
        except RedisRetryError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            _log_retry_exhausted(self.logger, config.context)
            return False
        else:
            return True


def _build_retry_policy(attempts: int, retry_delay: float) -> RedisRetryPolicy:
    return RedisRetryPolicy(
        max_attempts=max(1, attempts),
        initial_delay=max(0.01, retry_delay),
        max_delay=max(retry_delay * 4, retry_delay),
    )


def _create_retry_callback(context: str, log: logging.Logger) -> Callable:
    """Create retry callback function."""

    def _on_retry(retry_context: RedisRetryContext) -> None:
        log.warning(
            "%s: Redis connection failed (attempt %s/%s); retrying in %.2fs (%s)",
            context,
            retry_context.attempt,
            retry_context.max_attempts,
            retry_context.delay,
            retry_context.exception,
        )

    return _on_retry


def create_connection_operation(config: ConnectionOperationConfig) -> Callable:
    """Create connection operation function from config."""

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


def _create_connection_operation_from_retry(helper: ConnectionRetryHelper, retry_config: TradeStoreConnectionRetryConfig):
    config = ConnectionOperationConfig(
        connection_manager=helper.connection,
        pool_acquirer=retry_config.pool_acquirer,
        verify_func=retry_config.verify_func,
        close_func=retry_config.close_func,
        reset_func=retry_config.reset_func,
        redis_setter=retry_config.redis_setter,
        context=retry_config.context,
        attempts=retry_config.attempts,
        allow_reuse=retry_config.allow_reuse,
        logger=helper.logger,
    )
    return create_connection_operation(config)


def _log_retry_exhausted(log: logging.Logger, context: str) -> None:
    log.exception("%s: Redis connection retry exhausted", context)
