"""Tests for kalshi_catalog skipped_stats_store module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from common.kalshi_catalog.filtering import SkippedMarketStats
from common.kalshi_catalog.skipped_stats_store import (
    REDIS_KEY,
    TTL_SECONDS,
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
        stats.add_zero_volume()
        stats.add_zero_volume()

        await store_skipped_stats(redis, stats)

        redis.set.assert_awaited_once()
        args = redis.set.call_args
        assert args[0][0] == REDIS_KEY
        stored_data = json.loads(args[0][1])
        assert stored_data["total_skipped"] == 2
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
