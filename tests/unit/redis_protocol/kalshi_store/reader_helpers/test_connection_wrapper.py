import logging

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers.connection_wrapper import (
    ReaderConnectionWrapper,
)


class _DummyConnectionManager:
    def __init__(self):
        self.redis = object()

    async def get_redis(self):
        return self.redis

    async def ensure_connection(self):
        return True


def test_reader_connection_wrapper_getters(monkeypatch):
    conn = _DummyConnectionManager()
    wrapper = ReaderConnectionWrapper(conn, logger_instance=logging.getLogger("test"))

    assert hasattr(wrapper, "logger")


@pytest.mark.asyncio
async def test_ensure_or_raise_calls_helper(monkeypatch):
    conn = _DummyConnectionManager()
    events = {}

    async def ensure_or_raise(fn, *, operation, logger):
        events["operation"] = operation
        return await fn()

    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.connection_wrapper.ensure_or_raise",
        ensure_or_raise,
    )

    wrapper = ReaderConnectionWrapper(conn, logger_instance=logging.getLogger("test"))
    result = await wrapper.ensure_or_raise("op")
    assert events["operation"] == "op"
    assert result is conn.redis
