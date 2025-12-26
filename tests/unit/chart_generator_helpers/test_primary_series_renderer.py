"""Tests for chart_generator_helpers.primary_series_renderer module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from common.chart_generator.contexts import ChartStatistics, ChartTimeContext
from common.chart_generator_helpers.config import PrimarySeriesRenderConfig
from common.chart_generator_helpers.primary_series_renderer import PrimarySeriesRenderer


def make_time_context(timestamps: list) -> ChartTimeContext:
    """Create a ChartTimeContext with given timestamps."""
    return ChartTimeContext(
        naive=timestamps,
        prediction=None,
        axis=timestamps,
        localized=timestamps,
        local_timezone=timezone.utc,
        plot=timestamps,
    )


class TestPrimarySeriesRendererInit:
    """Tests for PrimarySeriesRenderer initialization."""

    def test_stores_colors(self) -> None:
        """Test stores color configuration."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")

        assert renderer.primary_color == "blue"
        assert renderer.secondary_color == "gray"


class TestPrimarySeriesRendererRenderPrimarySeries:
    """Tests for render_primary_series method."""

    def test_renders_pnl_chart_with_bars(self) -> None:
        """Test renders PnL chart with bar chart."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=-10, max_value=30, mean_value=10)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[10.0, -5.0, 15.0],
            plot_color="blue",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=True,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        result = renderer.render_primary_series(config=config)

        mock_ax.bar.assert_called_once()
        assert result is None

    def test_pnl_chart_uses_correct_colors(self) -> None:
        """Test PnL chart uses green for positive, red for negative."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=-10, max_value=30, mean_value=10)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[10.0, -5.0, 0.0],
            plot_color="blue",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=True,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        renderer.render_primary_series(config=config)

        call_args = mock_ax.bar.call_args
        colors = call_args[1]["color"]
        assert colors == ["green", "red", "green"]  # 0 is treated as >= 0

    def test_renders_temperature_chart_with_step(self) -> None:
        """Test renders temperature chart with step plot."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=70, max_value=80, mean_value=75)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[72.0, 75.0, 78.0],
            plot_color="orange",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        result = renderer.render_primary_series(config=config)

        mock_ax.fill_between.assert_called_once()
        mock_ax.step.assert_called_once()
        assert result is not None

    def test_renders_regular_chart_with_line(self) -> None:
        """Test renders regular chart with line plot."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[30.0, 50.0, 70.0],
            plot_color="green",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        result = renderer.render_primary_series(config=config)

        mock_ax.fill_between.assert_called_once()
        mock_ax.plot.assert_called_once()
        assert result is not None

    def test_returns_latest_timestamp_and_value(self) -> None:
        """Test returns latest timestamp and value for non-PnL charts."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[30.0, 50.0, 70.0],
            plot_color="green",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        result = renderer.render_primary_series(config=config)

        assert result[0] == now
        assert result[1] == 70.0

    def test_adds_mean_line_for_non_price_non_temperature(self) -> None:
        """Test adds horizontal mean line for regular charts."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[30.0, 50.0, 70.0],
            plot_color="green",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        renderer.render_primary_series(config=config)

        mock_ax.axhline.assert_called_once()
        call_kwargs = mock_ax.axhline.call_args[1]
        assert call_kwargs["y"] == 50.0
        assert call_kwargs["color"] == "gray"

    def test_no_mean_line_for_price_chart(self) -> None:
        """Test no mean line for price charts."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[30.0, 50.0, 70.0],
            plot_color="green",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            is_price_chart=True,
            mdates=mock_mdates,
        )

        renderer.render_primary_series(config=config)

        mock_ax.axhline.assert_not_called()

    def test_no_mean_line_for_temperature_chart(self) -> None:
        """Test no mean line for temperature charts."""
        renderer = PrimarySeriesRenderer(primary_color="blue", secondary_color="gray")
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_mdates.date2num.return_value = [1, 2, 3]
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now, now, now])
        stats = ChartStatistics(min_value=70, max_value=80, mean_value=75)

        config = PrimarySeriesRenderConfig(
            ax=mock_ax,
            values=[72.0, 75.0, 78.0],
            plot_color="orange",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            is_price_chart=False,
            mdates=mock_mdates,
        )

        renderer.render_primary_series(config=config)

        mock_ax.axhline.assert_not_called()
