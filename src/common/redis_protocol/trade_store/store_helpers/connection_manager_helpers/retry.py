"""Connection retry logic for TradeStore."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from ....retry import (
    RedisFatalError,
    RedisRetryError,
    RedisRetryPolicy,
    execute_with_retry,
)
from .base import ConnectionHelperBase
from .retry_helpers.callback_factory import create_retry_callback


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
        operation = _create_connection_operation(helper=self, retry_config=config)
        on_retry = _retry_logger(self.logger, config.context)

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
        except RedisRetryError as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            _log_retry_exhausted(self.logger, config.context, exc)
            return False
        else:
            return True


def _build_retry_policy(attempts: int, retry_delay: float) -> RedisRetryPolicy:
    return RedisRetryPolicy(
        max_attempts=max(1, attempts),
        initial_delay=max(0.01, retry_delay),
        max_delay=max(retry_delay * 4, retry_delay),
    )


def _create_connection_operation(helper: ConnectionRetryHelper, retry_config: TradeStoreConnectionRetryConfig):
    from .retry_helpers.operation_factory import (
        ConnectionOperationConfig,
        create_connection_operation,
    )

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


def _retry_logger(logger: logging.Logger, context: str):
    return create_retry_callback(context, logger)


def _log_retry_exhausted(logger: logging.Logger, context: str, exc: RedisRetryError) -> None:
    logger.exception("%s: Redis connection retry exhausted (%s)", context, exc)
