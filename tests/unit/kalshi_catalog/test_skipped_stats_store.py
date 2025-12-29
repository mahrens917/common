"""Tests for kalshi_catalog skipped_stats_store module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from common.kalshi_catalog.filtering import SkippedMarketStats
from common.kalshi_catalog.skipped_stats_store import (
    REDIS_KEY,
    TTL_SECONDS,
    get_skipped_stats,
    store_skipped_stats,
)


class TestStoreSkippedStats:
    """Tests for store_skipped_stats function."""

    @pytest.mark.asyncio
    async def test_stores_stats_in_redis(self) -> None:
        """Test stores skipped stats in Redis."""
        redis = AsyncMock()
        redis.set = AsyncMock()

        stats = SkippedMarketStats()
        stats.add_skipped("M1", "unsupported", "Crypto")
        stats.add_skipped("M2", "unsupported", "Weather")

        await store_skipped_stats(redis, stats)

        redis.set.assert_awaited_once()
        args = redis.set.call_args
        assert args[0][0] == REDIS_KEY
        stored_data = json.loads(args[0][1])
        assert stored_data["total_skipped"] == 2
        assert "unsupported" in stored_data["by_strike_type"]
        assert args[1]["ex"] == TTL_SECONDS

    @pytest.mark.asyncio
    async def test_stores_empty_stats(self) -> None:
        """Test stores empty stats when no markets skipped."""
        redis = AsyncMock()
        redis.set = AsyncMock()

        stats = SkippedMarketStats()
        await store_skipped_stats(redis, stats)

        redis.set.assert_awaited_once()
        args = redis.set.call_args
        stored_data = json.loads(args[0][1])
        assert stored_data["total_skipped"] == 0


class TestGetSkippedStats:
    """Tests for get_skipped_stats function."""

    @pytest.mark.asyncio
    async def test_retrieves_stats_from_redis(self) -> None:
        """Test retrieves skipped stats from Redis."""
        redis = AsyncMock()
        stored_data = {
            "timestamp": 1234567890,
            "total_skipped": 3,
            "by_strike_type": {"unsupported": ["M1", "M2"], "missing": ["M3"]},
            "by_category": {"Crypto": 2, "Weather": 1},
        }
        redis.get = AsyncMock(return_value=json.dumps(stored_data).encode())

        result = await get_skipped_stats(redis)

        assert result is not None
        assert result.total_skipped == 3
        assert result.by_strike_type == {"unsupported": ["M1", "M2"], "missing": ["M3"]}
        assert result.by_category == {"Crypto": 2, "Weather": 1}

    @pytest.mark.asyncio
    async def test_returns_none_when_key_missing(self) -> None:
        """Test returns None when Redis key doesn't exist."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)

        result = await get_skipped_stats(redis)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_json(self) -> None:
        """Test returns None when stored data is invalid JSON."""
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"invalid json")

        result = await get_skipped_stats(redis)

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_string_return(self) -> None:
        """Test handles Redis returning string instead of bytes."""
        redis = AsyncMock()
        stored_data = {
            "timestamp": 1234567890,
            "total_skipped": 1,
            "by_strike_type": {"unsupported": ["M1"]},
            "by_category": {"Crypto": 1},
        }
        redis.get = AsyncMock(return_value=json.dumps(stored_data))

        result = await get_skipped_stats(redis)

        assert result is not None
        assert result.total_skipped == 1

    @pytest.mark.asyncio
    async def test_handles_missing_fields_gracefully(self) -> None:
        """Test handles missing optional fields in stored data."""
        redis = AsyncMock()
        stored_data = {"timestamp": 1234567890}
        redis.get = AsyncMock(return_value=json.dumps(stored_data).encode())

        result = await get_skipped_stats(redis)

        assert result is not None
        assert result.total_skipped == 0
        assert result.by_strike_type == {}
        assert result.by_category == {}
