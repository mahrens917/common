import logging

import pytest

from src.common.redis_protocol.kalshi_store.subscription_helpers.connection_manager import (
    ConnectionManager,
)


class _DummyConnection:
    def __init__(self):
        self.ping_called = False

    async def get_redis(self):
        return self

    async def ping(self):
        self.ping_called = True


@pytest.mark.asyncio
async def test_get_redis_ok():
    fake = _DummyConnection()
    manager = ConnectionManager(fake, logger_instance=logging.getLogger("tests"))
    result = await manager.get_redis()
    assert result is fake
    assert fake.ping_called


@pytest.mark.asyncio
async def test_ensure_connection_or_raise_raises(monkeypatch):
    class BadConnection(_DummyConnection):
        async def get_redis(self):
            raise RuntimeError("fail")

    fake = BadConnection()
    manager = ConnectionManager(fake, logger_instance=logging.getLogger("tests"))
    with pytest.raises(RuntimeError):
        await manager.get_redis()
