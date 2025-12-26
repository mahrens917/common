"""Tests for chart_components.trade_visualization module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_components.trade_visualization import (
    _apply_trade_shadings,
    _close_visualizer,
    _render_trade_visualizations,
    _should_annotate,
    annotate_trades_if_needed,
)


class TestShouldAnnotate:
    """Tests for _should_annotate function."""

    def test_no_station_icao(self) -> None:
        """Test returns False when station_icao is None."""
        result = _should_annotate(None, True, [30.0], [datetime.now()])
        assert result is False

    def test_empty_station_icao(self) -> None:
        """Test returns False when station_icao is empty."""
        result = _should_annotate("", True, [30.0], [datetime.now()])
        assert result is False

    def test_not_temperature_chart(self) -> None:
        """Test returns False when not a temperature chart."""
        result = _should_annotate("KJFK", False, [30.0], [datetime.now()])
        assert result is False

    def test_no_kalshi_strikes(self) -> None:
        """Test returns False when no Kalshi strikes."""
        result = _should_annotate("KJFK", True, None, [datetime.now()])
        assert result is False

    def test_empty_kalshi_strikes(self) -> None:
        """Test returns False when Kalshi strikes empty."""
        result = _should_annotate("KJFK", True, [], [datetime.now()])
        assert result is False

    def test_no_naive_timestamps(self) -> None:
        """Test returns False when no naive timestamps."""
        result = _should_annotate("KJFK", True, [30.0], None)
        assert result is False

    def test_all_conditions_met(self) -> None:
        """Test returns True when all conditions met."""
        result = _should_annotate("KJFK", True, [30.0], [datetime.now()])
        assert result is True


class TestApplyTradeShadings:
    """Tests for _apply_trade_shadings function."""

    def test_no_shadings(self) -> None:
        """Test does nothing when no shadings."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()

        _apply_trade_shadings(mock_ax, mock_visualizer, [], [datetime.now()], "KJFK")

        mock_visualizer.apply_trade_shadings_to_chart.assert_not_called()

    def test_applies_shadings(self) -> None:
        """Test applies shadings to chart."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        shadings = [MagicMock()]
        timestamps = [datetime.now(timezone.utc)]

        _apply_trade_shadings(mock_ax, mock_visualizer, shadings, timestamps, "KJFK")

        mock_visualizer.apply_trade_shadings_to_chart.assert_called_once_with(mock_ax, shadings, timestamps)


class TestCloseVisualizer:
    """Tests for _close_visualizer function."""

    @pytest.mark.asyncio
    async def test_none_visualizer(self) -> None:
        """Test does nothing when visualizer is None."""
        await _close_visualizer(None, "KJFK")

    @pytest.mark.asyncio
    async def test_no_close_method(self) -> None:
        """Test does nothing when visualizer has no close method."""
        mock_visualizer = MagicMock(spec=[])
        await _close_visualizer(mock_visualizer, "KJFK")

    @pytest.mark.asyncio
    async def test_closes_visualizer(self) -> None:
        """Test closes visualizer successfully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock()

        await _close_visualizer(mock_visualizer, "KJFK")

        mock_visualizer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_close_error(self) -> None:
        """Test handles close error gracefully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock(side_effect=RuntimeError("Close failed"))

        await _close_visualizer(mock_visualizer, "KJFK")


class TestRenderTradeVisualizations:
    """Tests for _render_trade_visualizations function."""

    @pytest.mark.asyncio
    async def test_returns_on_init_failure(self) -> None:
        """Test returns when visualizer init fails."""
        mock_ax = MagicMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._initialize_visualizer",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await _render_trade_visualizations(
                ax=mock_ax,
                station_icao="KJFK",
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[30.0],
                trade_visualizer_cls=None,
            )

    @pytest.mark.asyncio
    async def test_renders_shadings(self) -> None:
        """Test renders trade shadings."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer.get_trade_shadings_for_station = AsyncMock(return_value=[])
        mock_visualizer.close = AsyncMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._initialize_visualizer",
            new_callable=AsyncMock,
            return_value=mock_visualizer,
        ):
            await _render_trade_visualizations(
                ax=mock_ax,
                station_icao="KJFK",
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[30.0],
                trade_visualizer_cls=None,
            )

        mock_visualizer.get_trade_shadings_for_station.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self) -> None:
        """Test handles RuntimeError gracefully."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer.get_trade_shadings_for_station = AsyncMock(side_effect=RuntimeError("API failed"))
        mock_visualizer.close = AsyncMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._initialize_visualizer",
            new_callable=AsyncMock,
            return_value=mock_visualizer,
        ):
            await _render_trade_visualizations(
                ax=mock_ax,
                station_icao="KJFK",
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[30.0],
                trade_visualizer_cls=None,
            )


class TestAnnotateTradesIfNeeded:
    """Tests for annotate_trades_if_needed function."""

    @pytest.mark.asyncio
    async def test_skips_when_should_not_annotate(self) -> None:
        """Test skips when should not annotate."""
        mock_ax = MagicMock()

        await annotate_trades_if_needed(
            ax=mock_ax,
            station_icao=None,
            naive_timestamps=None,
            plot_timestamps=[],
            is_temperature_chart=False,
            kalshi_strikes=None,
        )

    @pytest.mark.asyncio
    async def test_annotates_when_conditions_met(self) -> None:
        """Test annotates when conditions met."""
        mock_ax = MagicMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._render_trade_visualizations",
            new_callable=AsyncMock,
        ) as mock_render:
            await annotate_trades_if_needed(
                ax=mock_ax,
                station_icao="KJFK",
                naive_timestamps=[now],
                plot_timestamps=[now],
                is_temperature_chart=True,
                kalshi_strikes=[30.0],
            )

        mock_render.assert_called_once()
