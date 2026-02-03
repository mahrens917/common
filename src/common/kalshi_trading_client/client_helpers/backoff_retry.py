"""Backoff retry logic for KalshiTradingClient operations."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

from ...backoff_manager import BackoffManager
from ...backoff_manager_helpers import BackoffType
from ...kalshi_api.client import KalshiClientError

logger = logging.getLogger(__name__)

# Specific retryable errors for backoff retry (excludes RuntimeError to avoid broad handler)
BACKOFF_RETRY_ERRORS = (
    KalshiClientError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)

_T = TypeVar("_T")


async def with_backoff_retry(
    operation: Callable[[], Awaitable[_T]],
    *,
    backoff_manager: BackoffManager,
    service_name: str,
    backoff_type: BackoffType,
    context: str,
) -> _T:
    """Execute an operation with backoff retry on failure.

    On success, resets backoff state. On failure after HTTP-level
    retries are exhausted, uses backoff_manager to calculate delay
    and retries.
    """
    last_exc: Exception | None = None

    while backoff_manager.should_retry(service_name, backoff_type):
        try:
            result = await operation()
        except BACKOFF_RETRY_ERRORS as exc:  # Intentional retry loop  # policy_guard: allow-silent-handler
            last_exc = exc
            delay = backoff_manager.calculate_delay(service_name, backoff_type)
            logger.warning(
                "[%s] %s failed (%s), retrying in %.2fs",
                service_name,
                context,
                type(exc).__name__,
                delay,
            )
            await asyncio.sleep(delay)
        else:
            backoff_manager.reset_backoff(service_name, backoff_type)
            return result

    if last_exc is not None:
        raise last_exc

    raise RuntimeError(f"{context}: backoff exhausted with no prior exception")


__all__ = ["with_backoff_retry"]
