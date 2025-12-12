from __future__ import annotations

"""
Shared retry/backoff utilities for Redis interactions.

The helpers in this module provide a single place to configure retry policies
and calculate exponential backoff delays with jitter so that monitoring and
trading components behave consistently when Redis is unavailable.
"""


import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Protocol, Tuple, Type, TypeVar

from redis.exceptions import RedisError

_ResultT = TypeVar("_ResultT")


class _SupportsAwaitable(Protocol):
    def __call__(self, *args, **kwargs) -> Awaitable[None]:  # pragma: no cover - protocol
        ...


DEFAULT_RETRY_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
    RuntimeError,
    ValueError,
)


DEFAULT_REDIS_RETRY_MAX_DELAY = 2.0
DEFAULT_REDIS_RETRY_MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class RedisRetryPolicy:
    """Policy controlling retry/backoff behaviour."""

    max_attempts: int = DEFAULT_REDIS_RETRY_MAX_ATTEMPTS
    initial_delay: float = 0.2
    max_delay: float = DEFAULT_REDIS_RETRY_MAX_DELAY
    multiplier: float = 2.0
    jitter_ratio: float = 0.15
    retry_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRY_EXCEPTIONS


@dataclass(frozen=True)
class RedisRetryContext:
    """Metadata supplied to retry callbacks."""

    attempt: int
    max_attempts: int
    delay: float
    exception: Exception


class RedisRetryError(RuntimeError):
    """Raised when a retryable Redis operation exhausts all attempts."""


class RedisFatalError(RuntimeError):
    """Used by callers to abort further retries immediately."""


RetryCallback = Callable[[RedisRetryContext], Optional[Awaitable[None]]]
_SECURE_RANDOM = random.SystemRandom()


async def execute_with_retry(
    operation: Callable[[int], Awaitable[_ResultT]],
    *,
    policy: RedisRetryPolicy,
    logger: logging.Logger,
    context: str,
    on_retry: Optional[RetryCallback] = None,
) -> _ResultT:
    """
    Execute ``operation`` with a shared retry/backoff policy.

    Args:
        operation: Callable invoked for each attempt; receives the 1-based attempt index.
        policy: Retry timing configuration.
        logger: Logger used for default retry messages.
        context: Label describing the operation (used in logs).
        on_retry: Optional coroutine/callable invoked before each retry with details.

    Returns:
        The value returned by ``operation``.

    Raises:
        RedisRetryError: When the operation exhausts all retry attempts.
        RedisFatalError: When the operation signals a fatal condition.
    """

    delay = policy.initial_delay
    max_attempts = max(1, policy.max_attempts)

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation(attempt)
        except RedisFatalError:  # policy_guard: allow-silent-handler
            raise
        except policy.retry_exceptions as exc:
            if attempt >= max_attempts:
                raise RedisRetryError(f"{context} failed after {attempt} attempt(s)") from exc

            sleep_for = min(delay, policy.max_delay)
            jitter = sleep_for * policy.jitter_ratio
            if jitter > 0:
                sleep_for += _SECURE_RANDOM.uniform(-jitter, jitter)
            sleep_for = max(0.05, sleep_for)

            retry_context = RedisRetryContext(
                attempt=attempt,
                max_attempts=max_attempts,
                delay=sleep_for,
                exception=exc,
            )

            if on_retry is not None:
                await _maybe_await(on_retry(retry_context))
            else:
                logger.warning(
                    "%s failed on attempt %s/%s; retrying in %.2fs (%s)",
                    context,
                    attempt,
                    max_attempts,
                    sleep_for,
                    exc,
                )

            await asyncio.sleep(sleep_for)
            delay *= policy.multiplier

    raise RedisRetryError(f"{context} failed: unexpected retry loop exit")


async def _maybe_await(result: Optional[Awaitable[None]]) -> None:
    if result is None:
        return
    await result


__all__ = [
    "RedisFatalError",
    "RedisRetryContext",
    "RedisRetryError",
    "RedisRetryPolicy",
    "execute_with_retry",
]
