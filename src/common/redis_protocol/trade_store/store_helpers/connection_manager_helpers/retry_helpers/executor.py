"""Retry operation executor for ConnectionRetryHelper."""

import logging
from typing import Callable

from .....retry import RedisFatalError, RedisRetryError, RedisRetryPolicy, execute_with_retry


async def execute_retry_operation(
    operation: Callable,
    policy: RedisRetryPolicy,
    context: str,
    on_retry: Callable,
    logger: logging.Logger,
) -> bool:
    """Execute connection operation with retry logic."""
    try:
        await execute_with_retry(
            operation, policy=policy, logger=logger, context=context, on_retry=on_retry
        )
    except RedisFatalError:
        return False
    except RedisRetryError:
        logger.exception("%s: %s")
        return False
    else:
        return True
