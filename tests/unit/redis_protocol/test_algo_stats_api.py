"""Tests for algo_stats_api module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.algo_stats_api import (
    ALGO_STATS_KEY_PREFIX,
    ALGO_STATS_TTL_SECONDS,
    AlgoStatsData,
    increment_algo_stats,
    read_algo_stats,
    read_all_algo_stats,
    reset_algo_stats,
    write_algo_stats,
)


class TestAlgoStatsData:
    """Tests for AlgoStatsData dataclass."""

    def test_to_dict_converts_all_values_to_strings(self):
        stats = AlgoStatsData(
            algo="weather",
            events_processed=100,
            signals_generated=50,
            signals_written=45,
            ownership_rejections=5,
            markets_evaluated=200,
            last_updated="2025-01-01T12:00:00+00:00",
        )
        result = stats.to_dict()

        assert result["algo"] == "weather"
        assert result["events_processed"] == "100"
        assert result["signals_generated"] == "50"
        assert result["signals_written"] == "45"
        assert result["ownership_rejections"] == "5"
        assert result["markets_evaluated"] == "200"
        assert result["last_updated"] == "2025-01-01T12:00:00+00:00"

    def test_from_dict_creates_instance_with_defaults(self):
        data = {"algo": "pdf"}
        stats = AlgoStatsData.from_dict(data)

        assert stats.algo == "pdf"
        assert stats.events_processed == 0
        assert stats.signals_generated == 0
        assert stats.signals_written == 0
        assert stats.ownership_rejections == 0
        assert stats.markets_evaluated == 0
        assert stats.last_updated == ""

    def test_from_dict_parses_all_fields(self):
        data = {
            "algo": "peak",
            "events_processed": "100",
            "signals_generated": "50",
            "signals_written": "45",
            "ownership_rejections": "5",
            "markets_evaluated": "200",
            "last_updated": "2025-01-01T12:00:00+00:00",
        }
        stats = AlgoStatsData.from_dict(data)

        assert stats.algo == "peak"
        assert stats.events_processed == 100
        assert stats.signals_generated == 50
        assert stats.signals_written == 45
        assert stats.ownership_rejections == 5
        assert stats.markets_evaluated == 200
        assert stats.last_updated == "2025-01-01T12:00:00+00:00"


class TestWriteAlgoStats:
    """Tests for write_algo_stats function."""

    @pytest.mark.asyncio
    async def test_write_algo_stats_success(self):
        redis = MagicMock()
        redis.hset = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)

        result = await write_algo_stats(
            redis,
            algo="weather",
            events_processed=100,
            signals_generated=50,
            signals_written=45,
            ownership_rejections=5,
            markets_evaluated=200,
        )

        assert result is True
        redis.hset.assert_awaited_once()
        redis.expire.assert_awaited_once_with(f"{ALGO_STATS_KEY_PREFIX}:weather", ALGO_STATS_TTL_SECONDS)

    @pytest.mark.asyncio
    async def test_write_algo_stats_raises_on_redis_error(self):
        redis = MagicMock()
        redis.hset = AsyncMock(side_effect=RuntimeError("connection failed"))

        with pytest.raises(RuntimeError, match="connection failed"):
            await write_algo_stats(redis, algo="pdf", events_processed=10)


class TestIncrementAlgoStats:
    """Tests for increment_algo_stats function."""

    @pytest.mark.asyncio
    async def test_increment_algo_stats_success(self):
        mock_pipe = MagicMock()
        mock_pipe.hincrby = MagicMock()
        mock_pipe.hset = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[1, 1, 1, 1, 1])

        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=mock_pipe)

        result = await increment_algo_stats(
            redis,
            algo="weather",
            events_processed=10,
            signals_generated=5,
            signals_written=3,
            ownership_rejections=1,
            markets_evaluated=20,
        )

        assert result is True
        assert mock_pipe.hincrby.call_count == 5
        mock_pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increment_algo_stats_skips_zero_values(self):
        mock_pipe = MagicMock()
        mock_pipe.hincrby = MagicMock()
        mock_pipe.hset = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[1, 1, 1])

        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=mock_pipe)

        result = await increment_algo_stats(
            redis,
            algo="pdf",
            events_processed=10,
        )

        assert result is True
        mock_pipe.hincrby.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_algo_stats_raises_on_redis_error(self):
        mock_pipe = MagicMock()
        mock_pipe.hincrby = MagicMock()
        mock_pipe.hset = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("lost connection"))

        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=mock_pipe)

        with pytest.raises(ConnectionError, match="lost connection"):
            await increment_algo_stats(redis, algo="peak", events_processed=5)


class TestReadAlgoStats:
    """Tests for read_algo_stats function."""

    @pytest.mark.asyncio
    async def test_read_algo_stats_success(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(
            return_value={
                "algo": "weather",
                "events_processed": "100",
                "signals_generated": "50",
                "signals_written": "45",
                "ownership_rejections": "5",
                "markets_evaluated": "200",
                "last_updated": "2025-01-01T12:00:00+00:00",
            }
        )

        result = await read_algo_stats(redis, "weather")

        assert result is not None
        assert result.algo == "weather"
        assert result.events_processed == 100
        assert result.signals_generated == 50

    @pytest.mark.asyncio
    async def test_read_algo_stats_returns_none_for_missing_key(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(return_value={})

        result = await read_algo_stats(redis, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_read_algo_stats_handles_bytes(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(
            return_value={
                b"algo": b"pdf",
                b"events_processed": b"50",
            }
        )

        result = await read_algo_stats(redis, "pdf")

        assert result is not None
        assert result.algo == "pdf"
        assert result.events_processed == 50

    @pytest.mark.asyncio
    async def test_read_algo_stats_raises_on_redis_error(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(side_effect=OSError("network error"))

        with pytest.raises(OSError, match="network error"):
            await read_algo_stats(redis, "peak")


class TestReadAllAlgoStats:
    """Tests for read_all_algo_stats function."""

    @pytest.mark.asyncio
    async def test_read_all_algo_stats_returns_all_found(self):
        async def mock_hgetall(key):
            if "weather" in key:
                return {"algo": "weather", "events_processed": "100"}
            if "pdf" in key:
                return {"algo": "pdf", "events_processed": "50"}
            return {}

        redis = MagicMock()
        redis.hgetall = AsyncMock(side_effect=mock_hgetall)

        result = await read_all_algo_stats(redis)

        assert "weather" in result
        assert "pdf" in result
        assert result["weather"].events_processed == 100
        assert result["pdf"].events_processed == 50

    @pytest.mark.asyncio
    async def test_read_all_algo_stats_skips_missing(self):
        redis = MagicMock()
        redis.hgetall = AsyncMock(return_value={})

        result = await read_all_algo_stats(redis)

        assert result == {}


class TestResetAlgoStats:
    """Tests for reset_algo_stats function."""

    @pytest.mark.asyncio
    async def test_reset_algo_stats_success(self):
        redis = MagicMock()
        redis.delete = AsyncMock(return_value=1)

        result = await reset_algo_stats(redis, "weather")

        assert result is True
        redis.delete.assert_awaited_once_with(f"{ALGO_STATS_KEY_PREFIX}:weather")

    @pytest.mark.asyncio
    async def test_reset_algo_stats_raises_on_redis_error(self):
        redis = MagicMock()
        redis.delete = AsyncMock(side_effect=RuntimeError("redis down"))

        with pytest.raises(RuntimeError, match="redis down"):
            await reset_algo_stats(redis, "pdf")
