"""Retry callback factory for ConnectionRetryHelper."""

import logging
from typing import Callable

from .....retry import RedisRetryContext


def create_retry_callback(context: str, logger: logging.Logger) -> Callable:
    """Create retry callback function."""

    def _on_retry(retry_context: RedisRetryContext) -> None:
        logger.warning(
            "%s: Redis connection failed (attempt %s/%s); retrying in %.2fs (%s)",
            context,
            retry_context.attempt,
            retry_context.max_attempts,
            retry_context.delay,
            retry_context.exception,
        )

    return _on_retry
