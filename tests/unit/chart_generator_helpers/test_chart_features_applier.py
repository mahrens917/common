"""Tests for chart_generator_helpers.chart_features_applier module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_components.prediction_overlay import PredictionOverlayResult
from common.chart_generator.contexts import ChartStatistics, ChartTimeContext
from common.chart_generator_helpers.chart_features_applier import ChartFeaturesApplier
from common.chart_generator_helpers.config import ChartComponentData


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


class TestChartFeaturesApplierInit:
    """Tests for ChartFeaturesApplier initialization."""

    def test_stores_configure_time_axis_func(self) -> None:
        """Test stores configure_time_axis_func."""
        mock_func = MagicMock()
        applier = ChartFeaturesApplier(configure_time_axis_func=mock_func)

        assert applier.configure_time_axis_func is mock_func


class TestChartFeaturesApplierApplyAllFeatures:
    """Tests for apply_all_features method."""

    @pytest.mark.asyncio
    async def test_applies_chart_components(self) -> None:
        """Test applies chart components."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_format_y = MagicMock()
        mock_resolve_viz = MagicMock(return_value=MagicMock)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)
        overlay = PredictionOverlayResult(extrema=[])

        data = ChartComponentData(
            ax=mock_ax,
            values=[50.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=[],
            dawn_dusk_periods=[],
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=False,
            kalshi_strikes=None,
            chart_title="Test Chart",
            y_label="Y",
            station_icao=None,
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_features_applier.ChartComponentApplier") as mock_applier_cls:
            mock_applier = MagicMock()
            mock_applier_cls.return_value = mock_applier

            with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()):
                applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
                await applier.apply_all_features(
                    data=data,
                    format_y_axis_func=mock_format_y,
                    resolve_trade_visualizer_func=mock_resolve_viz,
                    station_coordinates=None,
                )

                mock_applier.apply_chart_components.assert_called_once()
                mock_configure_time.assert_called_once()

    @pytest.mark.asyncio
    async def test_configures_time_axis_for_temperature(self) -> None:
        """Test configures time axis for temperature chart."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_format_y = MagicMock()
        mock_resolve_viz = MagicMock(return_value=MagicMock)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=70, max_value=80, mean_value=75)
        overlay = PredictionOverlayResult(extrema=[])

        data = ChartComponentData(
            ax=mock_ax,
            values=[75.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=[],
            dawn_dusk_periods=[],
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=True,
            kalshi_strikes=None,
            chart_title="Temperature",
            y_label="",
            station_icao="KMIA",
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_features_applier.ChartComponentApplier"):
            with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()):
                applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
                await applier.apply_all_features(
                    data=data,
                    format_y_axis_func=mock_format_y,
                    resolve_trade_visualizer_func=mock_resolve_viz,
                    station_coordinates=(25.8, -80.3),
                )

                call_kwargs = mock_configure_time.call_args[1]
                assert call_kwargs["chart_type"] == "temperature"
                assert call_kwargs["station_coordinates"] == (25.8, -80.3)

    @pytest.mark.asyncio
    async def test_configures_time_axis_for_price(self) -> None:
        """Test configures time axis for price chart."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_format_y = MagicMock()
        mock_resolve_viz = MagicMock(return_value=MagicMock)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)
        overlay = PredictionOverlayResult(extrema=[])

        data = ChartComponentData(
            ax=mock_ax,
            values=[50.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=[],
            dawn_dusk_periods=[],
            is_pnl_chart=False,
            is_price_chart=True,
            is_temperature_chart=False,
            kalshi_strikes=None,
            chart_title="Price",
            y_label="$",
            station_icao=None,
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_features_applier.ChartComponentApplier"):
            with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()):
                applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
                await applier.apply_all_features(
                    data=data,
                    format_y_axis_func=mock_format_y,
                    resolve_trade_visualizer_func=mock_resolve_viz,
                    station_coordinates=None,
                )

                call_kwargs = mock_configure_time.call_args[1]
                assert call_kwargs["chart_type"] == "price"

    @pytest.mark.asyncio
    async def test_configures_time_axis_for_pnl(self) -> None:
        """Test configures time axis for PnL chart."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_format_y = MagicMock()
        mock_resolve_viz = MagicMock(return_value=MagicMock)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=-100, max_value=200, mean_value=50)
        overlay = PredictionOverlayResult(extrema=[])

        data = ChartComponentData(
            ax=mock_ax,
            values=[50.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=[],
            dawn_dusk_periods=[],
            is_pnl_chart=True,
            is_price_chart=False,
            is_temperature_chart=False,
            kalshi_strikes=None,
            chart_title="PnL",
            y_label="",
            station_icao=None,
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_features_applier.ChartComponentApplier"):
            with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()):
                applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
                await applier.apply_all_features(
                    data=data,
                    format_y_axis_func=mock_format_y,
                    resolve_trade_visualizer_func=mock_resolve_viz,
                    station_coordinates=None,
                )

                call_kwargs = mock_configure_time.call_args[1]
                assert call_kwargs["chart_type"] == "pnl"


class TestChartFeaturesApplierAnnotateTradesIfRequired:
    """Tests for _annotate_trades_if_required method."""

    @pytest.mark.asyncio
    async def test_calls_annotate_trades(self) -> None:
        """Test calls annotate_trades_if_needed."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_resolve_viz = MagicMock(return_value=MagicMock)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])

        with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()) as mock_annotate:
            applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
            await applier._annotate_trades_if_required(
                ax=mock_ax,
                station_icao="KMIA",
                time_context=time_context,
                is_temperature_chart=True,
                kalshi_strikes=[72.0, 75.0],
                resolve_trade_visualizer_func=mock_resolve_viz,
            )

            mock_annotate.assert_called_once()
            call_kwargs = mock_annotate.call_args[1]
            assert call_kwargs["ax"] is mock_ax
            assert call_kwargs["station_icao"] == "KMIA"
            assert call_kwargs["is_temperature_chart"] is True
            assert call_kwargs["kalshi_strikes"] == [72.0, 75.0]

    @pytest.mark.asyncio
    async def test_resolves_trade_visualizer(self) -> None:
        """Test resolves trade visualizer class."""
        mock_ax = MagicMock()
        mock_configure_time = MagicMock()
        mock_visualizer_cls = MagicMock()
        mock_resolve_viz = MagicMock(return_value=mock_visualizer_cls)

        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])

        with patch("common.chart_components.annotate_trades_if_needed", new=AsyncMock()) as mock_annotate:
            applier = ChartFeaturesApplier(configure_time_axis_func=mock_configure_time)
            await applier._annotate_trades_if_required(
                ax=mock_ax,
                station_icao=None,
                time_context=time_context,
                is_temperature_chart=False,
                kalshi_strikes=None,
                resolve_trade_visualizer_func=mock_resolve_viz,
            )

            mock_resolve_viz.assert_called_once()
            call_kwargs = mock_annotate.call_args[1]
            assert call_kwargs["trade_visualizer_cls"] is mock_visualizer_cls
