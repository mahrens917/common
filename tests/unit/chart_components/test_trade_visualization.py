"""Tests for chart_components.trade_visualization module."""

import asyncio
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

# Module-level test constants
TEST_STATION_ICAO = "KJFK"
TEST_STRIKE_LEVEL = 30.0


class TestShouldAnnotate:
    """Tests for _should_annotate function."""

    def test_no_station_icao(self) -> None:
        """Test returns False when station_icao is None."""
        result = _should_annotate(None, True, [TEST_STRIKE_LEVEL], [datetime.now()])
        assert result is False

    def test_empty_station_icao(self) -> None:
        """Test returns False when station_icao is empty."""
        result = _should_annotate("", True, [TEST_STRIKE_LEVEL], [datetime.now()])
        assert result is False

    def test_not_temperature_chart(self) -> None:
        """Test returns False when not a temperature chart."""
        result = _should_annotate(TEST_STATION_ICAO, False, [TEST_STRIKE_LEVEL], [datetime.now()])
        assert result is False

    def test_no_kalshi_strikes(self) -> None:
        """Test returns False when no Kalshi strikes."""
        result = _should_annotate(TEST_STATION_ICAO, True, None, [datetime.now()])
        assert result is False

    def test_empty_kalshi_strikes(self) -> None:
        """Test returns False when Kalshi strikes empty."""
        result = _should_annotate(TEST_STATION_ICAO, True, [], [datetime.now()])
        assert result is False

    def test_no_naive_timestamps(self) -> None:
        """Test returns False when no naive timestamps."""
        result = _should_annotate(TEST_STATION_ICAO, True, [TEST_STRIKE_LEVEL], None)
        assert result is False

    def test_all_conditions_met(self) -> None:
        """Test returns True when all conditions met."""
        result = _should_annotate(TEST_STATION_ICAO, True, [TEST_STRIKE_LEVEL], [datetime.now()])
        assert result is True


class TestApplyTradeShadings:
    """Tests for _apply_trade_shadings function."""

    def test_no_shadings(self) -> None:
        """Test does nothing when no shadings."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()

        _apply_trade_shadings(mock_ax, mock_visualizer, [], [datetime.now()], TEST_STATION_ICAO)

        mock_visualizer.apply_trade_shadings_to_chart.assert_not_called()

    def test_applies_shadings(self) -> None:
        """Test applies shadings to chart."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        shadings = [MagicMock()]
        timestamps = [datetime.now(timezone.utc)]

        _apply_trade_shadings(mock_ax, mock_visualizer, shadings, timestamps, TEST_STATION_ICAO)

        mock_visualizer.apply_trade_shadings_to_chart.assert_called_once_with(mock_ax, shadings, timestamps)


class TestCloseVisualizer:
    """Tests for _close_visualizer function."""

    @pytest.mark.asyncio
    async def test_none_visualizer(self) -> None:
        """Test does nothing when visualizer is None."""
        await _close_visualizer(None, TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_no_close_method(self) -> None:
        """Test does nothing when visualizer has no close method."""
        mock_visualizer = MagicMock(spec=[])
        await _close_visualizer(mock_visualizer, TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_closes_visualizer(self) -> None:
        """Test closes visualizer successfully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock()

        await _close_visualizer(mock_visualizer, TEST_STATION_ICAO)

        mock_visualizer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_close_error(self) -> None:
        """Test handles close error gracefully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock(side_effect=RuntimeError("Close failed"))

        await _close_visualizer(mock_visualizer, TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_handles_value_error(self) -> None:
        """Test handles ValueError gracefully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock(side_effect=ValueError("Invalid state"))

        await _close_visualizer(mock_visualizer, TEST_STATION_ICAO)

    @pytest.mark.asyncio
    async def test_handles_type_error(self) -> None:
        """Test handles TypeError gracefully."""
        mock_visualizer = MagicMock()
        mock_visualizer.close = AsyncMock(side_effect=TypeError("Type mismatch"))

        await _close_visualizer(mock_visualizer, TEST_STATION_ICAO)


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
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[TEST_STRIKE_LEVEL],
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
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[TEST_STRIKE_LEVEL],
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
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[TEST_STRIKE_LEVEL],
                trade_visualizer_cls=None,
            )

    @pytest.mark.asyncio
    async def test_handles_os_error(self) -> None:
        """Test handles OSError gracefully."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer.get_trade_shadings_for_station = AsyncMock(side_effect=OSError("Network error"))
        mock_visualizer.close = AsyncMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._initialize_visualizer",
            new_callable=AsyncMock,
            return_value=mock_visualizer,
        ):
            await _render_trade_visualizations(
                ax=mock_ax,
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[TEST_STRIKE_LEVEL],
                trade_visualizer_cls=None,
            )

    @pytest.mark.asyncio
    async def test_handles_value_error(self) -> None:
        """Test handles ValueError gracefully."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer.get_trade_shadings_for_station = AsyncMock(side_effect=ValueError("Invalid data"))
        mock_visualizer.close = AsyncMock()
        now = datetime.now(timezone.utc)

        with patch(
            "common.chart_components.trade_visualization._initialize_visualizer",
            new_callable=AsyncMock,
            return_value=mock_visualizer,
        ):
            await _render_trade_visualizations(
                ax=mock_ax,
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                kalshi_strikes=[TEST_STRIKE_LEVEL],
                trade_visualizer_cls=None,
            )

    @pytest.mark.asyncio
    async def test_reraises_cancelled_error(self) -> None:
        """Test re-raises CancelledError."""
        mock_ax = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer.get_trade_shadings_for_station = AsyncMock(side_effect=asyncio.CancelledError())
        mock_visualizer.close = AsyncMock()
        now = datetime.now(timezone.utc)

        with pytest.raises(asyncio.CancelledError):
            with patch(
                "common.chart_components.trade_visualization._initialize_visualizer",
                new_callable=AsyncMock,
                return_value=mock_visualizer,
            ):
                await _render_trade_visualizations(
                    ax=mock_ax,
                    station_icao=TEST_STATION_ICAO,
                    naive_timestamps=[now],
                    plot_timestamps=[now],
                    kalshi_strikes=[TEST_STRIKE_LEVEL],
                    trade_visualizer_cls=None,
                )


class TestInitializeVisualizerEdgeCases:
    """Tests for _initialize_visualizer edge cases that can be tested."""

    @pytest.mark.asyncio
    async def test_none_input_uses_default_class(self) -> None:
        """Test passing None uses default TradeVisualizer class."""
        # Import the function's module to patch TradeVisualizer in its namespace
        import common.chart_components.trade_visualization as tv_module
        from common.chart_components.trade_visualization import _initialize_visualizer

        mock_visualizer = MagicMock()
        mock_visualizer.initialize = AsyncMock(return_value=True)
        mock_trade_visualizer_cls = MagicMock(return_value=mock_visualizer)

        # Patch both the local import and the TYPE_CHECKING import
        with (
            patch.object(tv_module, "TradeVisualizer", mock_trade_visualizer_cls, create=True),
            patch("common.trade_visualizer.TradeVisualizer", mock_trade_visualizer_cls),
        ):
            result = await _initialize_visualizer(None)

        # Should have called the default class and returned the visualizer
        assert result == mock_visualizer
        mock_trade_visualizer_cls.assert_called()

    @pytest.mark.asyncio
    async def test_provided_class_used_when_given(self) -> None:
        """Test provided visualizer class is used when given."""
        import common.chart_components.trade_visualization as tv_module
        from common.chart_components.trade_visualization import _initialize_visualizer

        mock_visualizer = MagicMock()
        mock_visualizer.initialize = AsyncMock(return_value=True)
        mock_custom_cls = MagicMock(return_value=mock_visualizer)

        with patch.object(tv_module, "TradeVisualizer", create=True):
            result = await _initialize_visualizer(mock_custom_cls)

        assert result == mock_visualizer
        mock_custom_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_initialize_returns_false(self) -> None:
        """Test returns None when initialize() returns False."""
        import common.chart_components.trade_visualization as tv_module
        from common.chart_components.trade_visualization import _initialize_visualizer

        mock_visualizer = MagicMock()
        mock_visualizer.initialize = AsyncMock(return_value=False)
        mock_cls = MagicMock(return_value=mock_visualizer)

        with patch.object(tv_module, "TradeVisualizer", create=True):
            result = await _initialize_visualizer(mock_cls)

        assert result is None


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
                station_icao=TEST_STATION_ICAO,
                naive_timestamps=[now],
                plot_timestamps=[now],
                is_temperature_chart=True,
                kalshi_strikes=[TEST_STRIKE_LEVEL],
            )

        mock_render.assert_called_once()
