"""Tests for chart_generator_helpers.system_chart_creator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.system_chart_creator import SystemChartCreator


class TestSystemChartCreatorInit:
    """Tests for SystemChartCreator initialization."""

    def test_stores_primary_color(self) -> None:
        """Test stores primary color."""
        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector"):
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.primary_color == "red"

    def test_stores_generate_func(self) -> None:
        """Test stores generate unified chart function."""
        mock_func = MagicMock()

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector"):
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=mock_func,
                )

                assert creator.generate_unified_chart_func is mock_func

    def test_creates_metrics_collector(self) -> None:
        """Test creates SystemMetricsCollector."""
        mock_collector = MagicMock()

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_class:
            mock_class.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.metrics_collector is mock_collector

    def test_creates_title_formatter(self) -> None:
        """Test creates ChartTitleFormatter."""
        mock_formatter = MagicMock()

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector"):
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter") as mock_class:
                mock_class.return_value = mock_formatter
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.title_formatter is mock_formatter


class TestSystemChartCreatorCreateSystemChart:
    """Tests for create_system_chart method."""

    @pytest.mark.asyncio
    async def test_collects_system_metric_data(self) -> None:
        """Test collects system metric data."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_system_metric_data = AsyncMock(return_value=([now], [75.5]))
        mock_redis = MagicMock()
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_system_chart("cpu", 24, mock_redis)

                mock_collector.collect_system_metric_data.assert_called_once_with(mock_redis, "cpu", 24)

    @pytest.mark.asyncio
    async def test_formats_chart_title(self) -> None:
        """Test formats chart title for metric type."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_system_metric_data = AsyncMock(return_value=([now], [50.0]))
        mock_formatter = MagicMock()
        mock_formatter.format_system_chart_title.return_value = "CPU Usage"
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter") as mock_fmt:
                mock_fmt.return_value = mock_formatter
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_system_chart("cpu", 24, MagicMock())

                mock_formatter.format_system_chart_title.assert_called_once_with("cpu")

    @pytest.mark.asyncio
    async def test_calls_generate_func_with_params(self) -> None:
        """Test calls generate function with correct parameters."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        values = [80.0]
        mock_collector = MagicMock()
        mock_collector.collect_system_metric_data = AsyncMock(return_value=(timestamps, values))
        mock_formatter = MagicMock()
        mock_formatter.format_system_chart_title.return_value = "Memory Usage"
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter") as mock_fmt:
                mock_fmt.return_value = mock_formatter
                creator = SystemChartCreator(
                    primary_color="orange",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_system_chart("memory", 12, MagicMock())

                mock_generate.assert_called_once()
                call_kwargs = mock_generate.call_args[1]
                assert call_kwargs["timestamps"] == timestamps
                assert call_kwargs["values"] == values
                assert call_kwargs["chart_title"] == "Memory Usage"
                assert call_kwargs["line_color"] == "orange"

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns chart file path."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_system_metric_data = AsyncMock(return_value=([now], [60.0]))
        mock_generate = AsyncMock(return_value="/tmp/system_chart.png")

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=mock_generate,
                )

                result = await creator.create_system_chart("cpu", 24, MagicMock())

                assert result == "/tmp/system_chart.png"

    @pytest.mark.asyncio
    async def test_formatter_uses_percentage(self) -> None:
        """Test value formatter formats as percentage."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_system_metric_data = AsyncMock(return_value=([now], [75.5]))
        mock_generate = AsyncMock(return_value="/path/chart.png")

        with patch("common.chart_generator_helpers.system_chart_creator.SystemMetricsCollector") as mock_cls:
            mock_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.system_chart_creator.ChartTitleFormatter"):
                creator = SystemChartCreator(
                    primary_color="red",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_system_chart("cpu", 24, MagicMock())

                call_kwargs = mock_generate.call_args[1]
                formatter = call_kwargs["value_formatter_func"]
                assert formatter(75.5) == "75.5%"
