from __future__ import annotations

import asyncio
import logging

import pytest

from src.common.redis_protocol.retry import (
    RedisFatalError,
    RedisRetryContext,
    RedisRetryPolicy,
    execute_with_retry,
)


def _test_logger() -> logging.Logger:
    logger = logging.getLogger("redis_retry_test")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_first_attempt():
    attempts: list[int] = []

    async def op(attempt: int) -> str:
        attempts.append(attempt)
        return "ok"

    result = await execute_with_retry(
        op,
        policy=RedisRetryPolicy(max_attempts=3, jitter_ratio=0.0),
        logger=_test_logger(),
        context="test",
    )

    assert result == "ok"
    assert attempts == [1]


@pytest.mark.asyncio
async def test_execute_with_retry_invokes_retry_callback(monkeypatch: pytest.MonkeyPatch):
    attempts: list[int] = []
    sleeps: list[float] = []
    retries: list[RedisRetryContext] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def op(attempt: int) -> str:
        attempts.append(attempt)
        if attempt == 1:
            raise ValueError("boom")
        return "success"

    async def on_retry(ctx: RedisRetryContext) -> None:
        retries.append(ctx)

    policy = RedisRetryPolicy(
        max_attempts=3,
        initial_delay=0.05,
        max_delay=0.05,
        multiplier=1.0,
        jitter_ratio=0.0,
    )

    result = await execute_with_retry(
        op,
        policy=policy,
        logger=_test_logger(),
        context="retry_test",
        on_retry=on_retry,
    )

    assert result == "success"
    assert attempts == [1, 2]
    assert len(retries) == 1
    assert retries[0].attempt == 1
    assert sleeps == [pytest.approx(0.05, rel=1e-2)]


@pytest.mark.asyncio
async def test_execute_with_retry_stops_on_fatal_error():
    async def op(_: int) -> None:
        raise RedisFatalError("fatal")

    with pytest.raises(RedisFatalError):
        await execute_with_retry(
            op,
            policy=RedisRetryPolicy(max_attempts=3, jitter_ratio=0.0),
            logger=_test_logger(),
            context="fatal_test",
        )
