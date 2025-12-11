"""Tests for Kalshi store service status manager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.subscription_helpers import service_status_manager


class DummyRedisError(Exception):
    pass


class DummyRedis:
    def __init__(self):
        self.store = {}

    async def hset(self, key, field, value):
        self.store[(key, field)] = value

    async def hget(self, key, field):
        return self.store.get((key, field))


@pytest.mark.asyncio
async def test_service_status_string_or_default():
    assert service_status_manager.ServiceStatusManager._string_or_default(b"bytes") == "bytes"
    assert service_status_manager.ServiceStatusManager._string_or_default("ok") == "ok"
    assert service_status_manager.ServiceStatusManager._string_or_default(object()) == ""


@pytest.mark.asyncio
async def test_update_service_status_accepts_dict(monkeypatch):
    redis = DummyRedis()
    manager = service_status_manager.ServiceStatusManager(lambda: AsyncMock(return_value=redis)(), "status:key")

    status_dict = {"status": "healthy"}

    assert await manager.update_service_status("kalshi", status_dict)
    assert redis.store[("status:key", "kalshi")] == "healthy"


@pytest.mark.asyncio
async def test_update_service_status_handles_string(monkeypatch):
    redis = DummyRedis()
    manager = service_status_manager.ServiceStatusManager(lambda: AsyncMock(return_value=redis)(), "status:key")

    assert await manager.update_service_status("kalshi", "ok")
    assert redis.store[("status:key", "kalshi")] == "ok"


@pytest.mark.asyncio
async def test_update_service_status_raises_on_redis_error(monkeypatch):
    redis = MagicMock()
    redis.hset = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(service_status_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = service_status_manager.ServiceStatusManager(lambda: AsyncMock(return_value=redis)(), "status:key")

    with pytest.raises(DummyRedisError):
        await manager.update_service_status("kalshi", {"status": "ok"})


@pytest.mark.asyncio
async def test_get_service_status_returns_value(monkeypatch):
    redis = DummyRedis()
    redis.store[("status:key", "kalshi")] = "ready"
    manager = service_status_manager.ServiceStatusManager(lambda: AsyncMock(return_value=redis)(), "status:key")

    assert await manager.get_service_status("kalshi") == "ready"

    assert await manager.get_service_status("missing") is None


@pytest.mark.asyncio
async def test_get_service_status_error(monkeypatch):
    redis = MagicMock()
    redis.hget = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(service_status_manager, "REDIS_ERRORS", (DummyRedisError,))
    manager = service_status_manager.ServiceStatusManager(lambda: AsyncMock(return_value=redis)(), "status:key")

    with pytest.raises(DummyRedisError):
        await manager.get_service_status("kalshi")
