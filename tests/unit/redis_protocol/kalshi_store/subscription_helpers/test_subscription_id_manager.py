"""Tests for Kalshi store subscription id manager."""

from __future__ import annotations

from typing import Any, Dict, Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.subscription_helpers import (
    subscription_id_manager,
)


class DummyRedisError(Exception):
    pass


class DummyRedis:
    def __init__(self):
        self.storage: Dict[str, Any] = {}

    async def hset(self, key, mapping):
        self.storage.update(mapping)

    async def hmget(self, key, fields):
        return [self.storage.get(field) for field in fields]

    async def hdel(self, key, *fields):
        for field in fields:
            self.storage.pop(field, None)


@pytest.mark.asyncio
async def test_record_subscription_ids_skips_invalid(monkeypatch):
    redis = DummyRedis()
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    class ValueThatRaises:
        def __str__(self):
            raise TypeError("boom")

    await manager.record_subscription_ids({"first": "1", "bad": ValueThatRaises()})

    assert "ws:first" in redis.storage
    assert "ws:bad" not in redis.storage

    # verify nothing happens when payload empty
    await manager.record_subscription_ids({})


@pytest.mark.asyncio
async def test_record_subscription_ids_raises_on_error(monkeypatch):
    redis = MagicMock()
    redis.hset = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(subscription_id_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    with pytest.raises(DummyRedisError):
        await manager.record_subscription_ids({"first": "1"})


@pytest.mark.asyncio
async def test_fetch_subscription_ids_returns_values(monkeypatch):
    redis = DummyRedis()
    redis.storage["ws:first"] = "1"
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    result = await manager.fetch_subscription_ids(["first", "missing"])

    assert result == {"first": "1"}


@pytest.mark.asyncio
async def test_fetch_subscription_ids_handles_errors(monkeypatch):
    redis = MagicMock()
    redis.hmget = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(subscription_id_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    with pytest.raises(DummyRedisError):
        await manager.fetch_subscription_ids(["first"])


@pytest.mark.asyncio
async def test_clear_subscription_ids(monkeypatch):
    redis = DummyRedis()
    redis.storage["ws:first"] = "1"
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    await manager.clear_subscription_ids(["first"])
    assert "ws:first" not in redis.storage


@pytest.mark.asyncio
async def test_clear_subscription_ids_handles_error(monkeypatch):
    redis = MagicMock()
    redis.hdel = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(subscription_id_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = subscription_id_manager.SubscriptionIdManager(
        lambda: AsyncMock(return_value=redis)(), "subs:key", "ws"
    )

    with pytest.raises(DummyRedisError):
        await manager.clear_subscription_ids(["first"])
