"""
Retry handling for RedisConnectionManager
"""

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from redis.asyncio import Redis

from ...retry import (
    RedisFatalError,
    RedisRetryContext,
    RedisRetryError,
    RedisRetryPolicy,
    execute_with_retry,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionRetryConfig:
    """Configuration for Redis connection retry operations."""

    allow_reuse: bool
    context: str
    attempts: int
    retry_delay: float
    pool_acquirer: Callable
    connection_verifier: Callable
    on_success: Callable[[Redis], None]
    on_failure: Callable[[], None]
    close_client: Callable[[Redis], Awaitable[None]]


class RetryHandler:
    """Handles retry logic for Redis connections"""

    def __init__(self, logger_instance: logging.Logger):
        """
        Initialize retry handler

        Args:
            logger_instance: Logger for retry messages
        """
        self._logger = logger_instance

    async def connect_with_retry(self, config: ConnectionRetryConfig) -> bool:
        """
        Connect to Redis with retry logic

        Args:
            config: Configuration for connection retry operations

        Returns:
            True if connection successful, False otherwise
        """
        policy = RedisRetryPolicy(
            max_attempts=max(1, config.attempts),
            initial_delay=max(0.01, config.retry_delay),
            max_delay=max(config.retry_delay * 4, config.retry_delay),
        )

        async def _operation(attempt: int) -> Redis:
            redis_client = await config.pool_acquirer(allow_reuse=config.allow_reuse)
            self._logger.debug(
                "%s: verifying Redis connection (attempt %s/%s)",
                config.context,
                attempt,
                config.attempts,
            )
            ok, fatal = await config.connection_verifier(redis_client)
            if ok:
                config.on_success(redis_client)
                self._logger.debug("%s: Redis connection established", config.context)
                return redis_client

            await config.close_client(redis_client)
            config.on_failure()

            if fatal:
                raise RedisFatalError("event loop shutting down during Redis ping")

            raise RuntimeError("Redis connection failed health check")

        def _on_retry(retry_context: RedisRetryContext) -> None:
            self._logger.warning(
                "%s: Redis connection failed (attempt %s/%s); retrying in %.2fs (%s)",
                config.context,
                retry_context.attempt,
                retry_context.max_attempts,
                retry_context.delay,
                retry_context.exception,
            )

        try:
            await execute_with_retry(
                _operation,
                policy=policy,
                logger=self._logger,
                context=config.context,
                on_retry=_on_retry,
            )
        except RedisFatalError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.debug("Expected exception, returning default value")
            return False
        except RedisRetryError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            self._logger.exception("%s: %s")
            return False
        else:
            return True
