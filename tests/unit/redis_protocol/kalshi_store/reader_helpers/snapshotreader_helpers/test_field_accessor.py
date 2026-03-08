"""Tests for Kalshi store snapshot reader helpers."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

import common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader as helpers
from common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader import SnapshotReader


class DummyRedisError(Exception):
    pass


def _make_reader():
    return SnapshotReader(
        logger_instance=logging.getLogger(__name__),
        metadata_extractor=MagicMock(),
        metadata_adapter=MagicMock(),
    )


@pytest.mark.asyncio
async def test_get_market_field_returns_value():
    redis = MagicMock()
    redis.hget = AsyncMock(return_value=b"value")
    reader = _make_reader()

    result = await reader.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == b"value"
    redis.hget.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_market_field_missing_returns_empty():
    redis = MagicMock()
    redis.hget = AsyncMock(return_value=None)
    reader = _make_reader()

    result = await reader.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == ""


@pytest.mark.asyncio
async def test_get_market_field_logs_error_and_returns_empty(monkeypatch):
    redis = MagicMock()
    redis.hget = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(helpers, "REDIS_ERRORS", (DummyRedisError,))
    reader = _make_reader()

    result = await reader.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == ""


@pytest.mark.asyncio
async def test_is_market_tracked_returns_true():
    redis = MagicMock()
    redis.exists = AsyncMock(return_value=1)
    reader = _make_reader()

    result = await reader.is_market_tracked(redis, "market:key", "KXHIGHTEST")

    assert result
    redis.exists.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_market_tracked_raises_on_error(monkeypatch):
    redis = MagicMock()
    redis.exists = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(helpers, "REDIS_ERRORS", (DummyRedisError,))
    reader = _make_reader()

    with pytest.raises(DummyRedisError):
        await reader.is_market_tracked(redis, "market:key", "KXHIGHTEST")
