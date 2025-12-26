"""Tests for chart_generator_helpers.system_metrics_collector module."""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.system_metrics_collector import SystemMetricsCollector


class TestSystemMetricsCollectorCollectSystemMetricData:
    """Tests for collect_system_metric_data method."""

    @pytest.mark.asyncio
    async def test_collects_cpu_metrics(self) -> None:
        """Test collects CPU metrics from Redis."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str: "45.5",
                datetime_str2: "50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            assert len(timestamps) == 2
            assert 45.5 in values
            assert 50.0 in values

    @pytest.mark.asyncio
    async def test_raises_on_empty_data(self) -> None:
        """Test raises InsufficientDataError on empty data."""
        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={})

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()

            with pytest.raises(InsufficientDataError) as exc_info:
                await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            assert "cpu" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_insufficient_data_points(self) -> None:
        """Test raises InsufficientDataError on insufficient data points."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(return_value={datetime_str: "45.5"})

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()

            with pytest.raises(InsufficientDataError) as exc_info:
                await collector.collect_system_metric_data(mock_redis, "memory", 24)

            assert "Insufficient data points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_bytes_data(self) -> None:
        """Test handles bytes data from Redis."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str.encode(): b"45.5",
                datetime_str2.encode(): b"50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            assert len(timestamps) == 2

    @pytest.mark.asyncio
    async def test_filters_by_time_window(self) -> None:
        """Test filters data by time window."""
        now = datetime.now(tz=timezone.utc)
        recent_str = now.strftime("%Y-%m-%d %H:%M:%S")
        recent_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")
        old_str = "2020-01-01 00:00:00"  # Old data point

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                recent_str: "45.5",
                recent_str2: "50.0",
                old_str: "30.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 1)  # 1 hour

            # Old data point should be filtered out
            assert len(timestamps) == 2

    @pytest.mark.asyncio
    async def test_skips_zero_values(self) -> None:
        """Test skips zero values."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")
        datetime_str3 = (now.replace(minute=now.minute - 2 if now.minute > 1 else 58)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str: "0.0",
                datetime_str2: "45.5",
                datetime_str3: "50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "memory", 24)

            assert len(timestamps) == 2
            assert 0.0 not in values

    @pytest.mark.asyncio
    async def test_skips_invalid_datetime(self, caplog) -> None:
        """Test skips entries with invalid datetime format."""
        now = datetime.now(tz=timezone.utc)
        valid_str = now.strftime("%Y-%m-%d %H:%M:%S")
        valid_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                "invalid-date": "45.5",
                valid_str: "50.0",
                valid_str2: "55.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            assert len(timestamps) == 2

    @pytest.mark.asyncio
    async def test_skips_invalid_value(self, caplog) -> None:
        """Test skips entries with invalid numeric values."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")
        datetime_str3 = (now.replace(minute=now.minute - 2 if now.minute > 1 else 58)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str: "invalid",
                datetime_str2: "45.5",
                datetime_str3: "50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            assert len(timestamps) == 2

    @pytest.mark.asyncio
    async def test_returns_sorted_data(self) -> None:
        """Test returns data sorted by timestamp."""
        now = datetime.now(tz=timezone.utc)
        early_str = (now.replace(minute=10)).strftime("%Y-%m-%d %H:%M:%S")
        mid_str = (now.replace(minute=20)).strftime("%Y-%m-%d %H:%M:%S")
        late_str = (now.replace(minute=30)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                late_str: "30.0",
                early_str: "10.0",
                mid_str: "20.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            # Should be sorted by timestamp
            assert timestamps[0] < timestamps[1] < timestamps[2]
            assert values == [10.0, 20.0, 30.0]

    @pytest.mark.asyncio
    async def test_returns_timezone_aware_timestamps(self) -> None:
        """Test returns timezone-aware timestamps."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str: "45.5",
                datetime_str2: "50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            timestamps, values = await collector.collect_system_metric_data(mock_redis, "cpu", 24)

            for ts in timestamps:
                assert ts.tzinfo is not None

    @pytest.mark.asyncio
    async def test_uses_correct_redis_key(self) -> None:
        """Test uses correct Redis key format."""
        now = datetime.now(tz=timezone.utc)
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        datetime_str2 = (now.replace(minute=now.minute - 1 if now.minute > 0 else 59)).strftime("%Y-%m-%d %H:%M:%S")

        mock_redis = MagicMock()
        mock_redis.hgetall = MagicMock(
            return_value={
                datetime_str: "45.5",
                datetime_str2: "50.0",
            }
        )

        with patch("common.chart_generator_helpers.system_metrics_collector.ensure_awaitable", new=AsyncMock(side_effect=lambda x: x)):
            collector = SystemMetricsCollector()
            await collector.collect_system_metric_data(mock_redis, "memory", 24)

            mock_redis.hgetall.assert_called_once_with("history:memory")
