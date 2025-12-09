"""Tests for Kalshi store snapshot reader helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers import (
    field_accessor,
    market_tracker,
)


class DummyRedisError(Exception):
    pass


@pytest.mark.asyncio
async def test_get_market_field_returns_value():
    redis = MagicMock()
    redis.hget = AsyncMock(return_value=b"value")

    result = await field_accessor.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == b"value"
    redis.hget.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_market_field_missing_returns_empty():
    redis = MagicMock()
    redis.hget = AsyncMock(return_value=None)

    result = await field_accessor.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == ""


@pytest.mark.asyncio
async def test_get_market_field_logs_error_and_returns_empty(monkeypatch):
    redis = MagicMock()
    redis.hget = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(field_accessor, "REDIS_ERRORS", (DummyRedisError,))

    result = await field_accessor.get_market_field(redis, "market:key", "KXHIGHTEST", "status")

    assert result == ""


@pytest.mark.asyncio
async def test_is_market_tracked_returns_true():
    redis = MagicMock()
    redis.exists = AsyncMock(return_value=1)

    result = await market_tracker.is_market_tracked(redis, "market:key", "KXHIGHTEST")

    assert result
    redis.exists.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_market_tracked_raises_on_error(monkeypatch):
    redis = MagicMock()
    redis.exists = AsyncMock(side_effect=DummyRedisError("boom"))
    monkeypatch.setattr(market_tracker, "REDIS_ERRORS", (DummyRedisError,))

    with pytest.raises(DummyRedisError):
        await market_tracker.is_market_tracked(redis, "market:key", "KXHIGHTEST")
