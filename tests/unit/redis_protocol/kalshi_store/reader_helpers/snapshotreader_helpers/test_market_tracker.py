"""Tests for market tracker helper."""

import logging
from unittest.mock import MagicMock

import pytest

import common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader as helpers
from common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader import SnapshotReader


class DummyRedisError(Exception):
    pass


class StubRedis:
    async def exists(self, key):
        return 1


def _make_reader():
    return SnapshotReader(
        logger_instance=logging.getLogger(__name__),
        metadata_extractor=MagicMock(),
        metadata_adapter=MagicMock(),
    )


@pytest.mark.asyncio
async def test_is_market_tracked_returns_true():
    redis = StubRedis()
    reader = _make_reader()
    assert await reader.is_market_tracked(redis, "market", "T")


@pytest.mark.asyncio
async def test_is_market_tracked_raises_on_error(monkeypatch):
    class BrokenRedis:
        async def exists(self, *_, **__):
            raise DummyRedisError("boom")

    monkeypatch.setattr(helpers, "REDIS_ERRORS", (DummyRedisError,))
    reader = _make_reader()
    with pytest.raises(DummyRedisError):
        await reader.is_market_tracked(BrokenRedis(), "market", "T")
