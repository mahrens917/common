"""Tests for distributed lock helper factories."""

import pytest

from common.utils.distributed_lock_helpers.factory import (
    create_liquidation_lock,
    create_trade_lock,
)


class DummyLock:
    def __init__(self, redis_client, lock_key, timeout_seconds):
        self.redis_client = redis_client
        self.lock_key = lock_key
        self.timeout_seconds = timeout_seconds


@pytest.mark.asyncio
async def test_create_trade_lock(monkeypatch):
    monkeypatch.setattr(
        "common.utils.distributed_lock_helpers.factory.DistributedLock",
        DummyLock,
    )

    lock = await create_trade_lock("client", "TICKER", timeout_seconds=5)
    assert isinstance(lock, DummyLock)
    assert lock.lock_key == "trade_lock:TICKER"
    assert lock.timeout_seconds == 5


@pytest.mark.asyncio
async def test_create_liquidation_lock(monkeypatch):
    monkeypatch.setattr(
        "common.utils.distributed_lock_helpers.factory.DistributedLock",
        DummyLock,
    )

    lock = await create_liquidation_lock("client", "TICKER", timeout_seconds=10)
    assert isinstance(lock, DummyLock)
    assert lock.lock_key == "liquidation_lock:TICKER"
    assert lock.timeout_seconds == 10
