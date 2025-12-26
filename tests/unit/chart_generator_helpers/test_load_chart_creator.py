"""Tests for chart_generator_helpers.load_chart_creator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.load_chart_creator import LoadChartCreator


class TestLoadChartCreatorInit:
    """Tests for LoadChartCreator initialization."""

    def test_stores_primary_color(self) -> None:
        """Test stores primary color."""
        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector"):
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter"):
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.primary_color == "blue"

    def test_stores_generate_func(self) -> None:
        """Test stores generate unified chart function."""
        mock_func = MagicMock()

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector"):
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter"):
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=mock_func,
                )

                assert creator.generate_unified_chart_func is mock_func

    def test_creates_load_collector(self) -> None:
        """Test creates LoadDataCollector."""
        mock_collector = MagicMock()

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector") as mock_class:
            mock_class.return_value = mock_collector
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter"):
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.load_collector is mock_collector

    def test_creates_title_formatter(self) -> None:
        """Test creates ChartTitleFormatter."""
        mock_formatter = MagicMock()

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector"):
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter") as mock_class:
                mock_class.return_value = mock_formatter
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=MagicMock(),
                )

                assert creator.title_formatter is mock_formatter


class TestLoadChartCreatorCreateLoadChart:
    """Tests for create_load_chart method."""

    @pytest.mark.asyncio
    async def test_collects_load_data(self) -> None:
        """Test collects load data for service."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_service_load_data = AsyncMock(return_value=([now], [100.0]))
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector") as mock_collector_cls:
            mock_collector_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter"):
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_load_chart("kalshi", 24)

                mock_collector.collect_service_load_data.assert_called_once_with("kalshi", 24)

    @pytest.mark.asyncio
    async def test_formats_chart_title(self) -> None:
        """Test formats chart title for service."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_service_load_data = AsyncMock(return_value=([now], [100.0]))
        mock_formatter = MagicMock()
        mock_formatter.format_load_chart_title.return_value = "Load: Kalshi"
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector") as mock_collector_cls:
            mock_collector_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter") as mock_fmt_cls:
                mock_fmt_cls.return_value = mock_formatter
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_load_chart("kalshi", 24)

                mock_formatter.format_load_chart_title.assert_called_once_with("kalshi")

    @pytest.mark.asyncio
    async def test_calls_generate_func_with_params(self) -> None:
        """Test calls generate function with correct parameters."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        values = [100.0]
        mock_collector = MagicMock()
        mock_collector.collect_service_load_data = AsyncMock(return_value=(timestamps, values))
        mock_formatter = MagicMock()
        mock_formatter.format_load_chart_title.return_value = "Load: Test"
        mock_generate = AsyncMock(return_value="/path/to/chart.png")

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector") as mock_collector_cls:
            mock_collector_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter") as mock_fmt_cls:
                mock_fmt_cls.return_value = mock_formatter
                creator = LoadChartCreator(
                    primary_color="green",
                    generate_unified_chart_func=mock_generate,
                )

                await creator.create_load_chart("service", 12)

                mock_generate.assert_called_once()
                call_kwargs = mock_generate.call_args[1]
                assert call_kwargs["timestamps"] == timestamps
                assert call_kwargs["values"] == values
                assert call_kwargs["chart_title"] == "Load: Test"
                assert call_kwargs["line_color"] == "green"

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns chart file path."""
        from datetime import datetime, timezone

        now = datetime.now(tz=timezone.utc)
        mock_collector = MagicMock()
        mock_collector.collect_service_load_data = AsyncMock(return_value=([now], [100.0]))
        mock_generate = AsyncMock(return_value="/tmp/load_chart.png")

        with patch("common.chart_generator_helpers.load_chart_creator.LoadDataCollector") as mock_collector_cls:
            mock_collector_cls.return_value = mock_collector
            with patch("common.chart_generator_helpers.load_chart_creator.ChartTitleFormatter"):
                creator = LoadChartCreator(
                    primary_color="blue",
                    generate_unified_chart_func=mock_generate,
                )

                result = await creator.create_load_chart("service", 24)

                assert result == "/tmp/load_chart.png"
