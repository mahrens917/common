"""Tests for market tracker helper."""

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers import (
    market_tracker,
)


class DummyRedisError(Exception):
    pass


class StubRedis:
    async def exists(self, key):
        return 1


@pytest.mark.asyncio
async def test_is_market_tracked_returns_true():
    redis = StubRedis()
    assert await market_tracker.is_market_tracked(redis, "market", "T")


@pytest.mark.asyncio
async def test_is_market_tracked_raises_on_error(monkeypatch):
    class BrokenRedis:
        async def exists(self, *_, **__):
            raise DummyRedisError("boom")

    monkeypatch.setattr(market_tracker, "REDIS_ERRORS", (DummyRedisError,))
    with pytest.raises(DummyRedisError):
        await market_tracker.is_market_tracked(BrokenRedis(), "market", "T")
