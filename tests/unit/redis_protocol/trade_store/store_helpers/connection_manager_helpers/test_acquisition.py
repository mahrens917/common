"""Tests for TradeStore connection acquisition helper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.trade_store.errors import TradeStoreError
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers import (
    acquisition,
)


class DummyConnectionManager:
    def __init__(self, initialized: bool = True):
        self.initialized = initialized


@pytest.mark.asyncio
async def test_get_redis_returns_client_when_available():
    manager = DummyConnectionManager()
    helper = acquisition.ConnectionAcquisitionHelper(logger=MagicMock(), connection_manager=manager)
    redis_client = object()

    getter = lambda: redis_client
    ensure = AsyncMock(return_value=True)
    ping = AsyncMock(return_value=(True, False))

    result = await helper.get_redis(getter, ensure, ping)

    assert result is redis_client
    ping.assert_awaited_once_with(redis_client)


@pytest.mark.asyncio
async def test_get_redis_retries_when_client_missing(monkeypatch):
    manager = DummyConnectionManager(initialized=True)
    helper = acquisition.ConnectionAcquisitionHelper(logger=MagicMock(), connection_manager=manager)
    redis_state = {"client": None}

    def getter():
        return redis_state["client"]

    async def ensure_func():
        if redis_state["client"] is None:
            redis_state["client"] = object()
            return False
        return True

    ensure = AsyncMock(side_effect=ensure_func)
    ping = AsyncMock(return_value=(True, False))

    result = await helper.get_redis(getter, ensure, ping)
    assert result is redis_state["client"]


@pytest.mark.asyncio
async def test_get_redis_raises_when_ensure_fails(monkeypatch):
    manager = DummyConnectionManager()
    helper = acquisition.ConnectionAcquisitionHelper(logger=MagicMock(), connection_manager=manager)

    getter = lambda: None
    ensure = AsyncMock(return_value=False)
    ping = AsyncMock()

    with pytest.raises(TradeStoreError):
        await helper.get_redis(getter, ensure, ping)


@pytest.mark.asyncio
async def test_get_redis_raises_when_ping_fails_fatal(monkeypatch):
    manager = DummyConnectionManager()
    helper = acquisition.ConnectionAcquisitionHelper(logger=MagicMock(), connection_manager=manager)
    redis = object()

    getter = lambda: redis
    ensure = AsyncMock(return_value=True)
    ping = AsyncMock(return_value=(False, True))

    with pytest.raises(TradeStoreError):
        await helper.get_redis(getter, ensure, ping)


@pytest.mark.asyncio
async def test_get_redis_reconnects_after_nonfatal_ping_failure(monkeypatch):
    manager = DummyConnectionManager()
    helper = acquisition.ConnectionAcquisitionHelper(logger=MagicMock(), connection_manager=manager)
    redis_state = {"client": object(), "reconnected": object()}

    def getter():
        return redis_state["client"]

    call_index = {"count": 0}

    async def ensure_func():
        call_index["count"] += 1
        if call_index["count"] == 2:
            redis_state["client"] = redis_state["reconnected"]
        return True

    ensure = AsyncMock(side_effect=ensure_func)
    ping = AsyncMock(return_value=(False, False))

    result = await helper.get_redis(getter, ensure, ping)
    assert result == redis_state["reconnected"]
