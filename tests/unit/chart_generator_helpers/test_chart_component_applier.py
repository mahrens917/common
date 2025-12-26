"""Tests for chart_generator_helpers.chart_component_applier module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.chart_components.prediction_overlay import PredictionOverlayResult
from common.chart_generator.contexts import ChartStatistics, ChartTimeContext
from common.chart_generator_helpers.chart_component_applier import ChartComponentApplier
from common.chart_generator_helpers.config import ChartComponentData, StatisticsFormattingConfig


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


class TestChartComponentApplierApplyChartComponents:
    """Tests for apply_chart_components method."""

    def test_adds_vertical_line_annotations(self) -> None:
        """Test adds vertical line annotations."""
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)
        overlay = PredictionOverlayResult(extrema=[])
        mock_vertical_lines = MagicMock()

        data = ChartComponentData(
            ax=mock_ax,
            values=[50.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=mock_vertical_lines,
            dawn_dusk_periods=[],
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=False,
            kalshi_strikes=None,
            chart_title="Test",
            y_label="Y",
            station_icao=None,
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_component_applier.add_vertical_line_annotations") as mock_add:
            with patch("common.chart_generator_helpers.chart_component_applier.AxesLimitsConfigurator"):
                with patch("common.chart_generator_helpers.chart_component_applier.ChartTitlesLabelsApplier"):
                    applier = ChartComponentApplier()
                    applier.apply_chart_components(data=data)

                    mock_add.assert_called_once()
                    call_kwargs = mock_add.call_args[1]
                    assert call_kwargs["is_temperature_chart"] is False

    def test_adds_dawn_dusk_shading_for_temperature(self) -> None:
        """Test adds dawn/dusk shading for temperature charts."""
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=70, max_value=80, mean_value=75)
        overlay = PredictionOverlayResult(extrema=[])
        mock_dawn_dusk = MagicMock()

        data = ChartComponentData(
            ax=mock_ax,
            values=[75.0],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay,
            prediction_values=None,
            prediction_uncertainties=None,
            vertical_lines=[],
            dawn_dusk_periods=mock_dawn_dusk,
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

        with patch("common.chart_generator_helpers.chart_component_applier.add_vertical_line_annotations"):
            with patch("common.chart_generator_helpers.chart_component_applier.add_dawn_dusk_shading") as mock_shading:
                with patch("common.chart_generator_helpers.chart_component_applier.AxesLimitsConfigurator"):
                    with patch("common.chart_generator_helpers.chart_component_applier.ChartTitlesLabelsApplier"):
                        applier = ChartComponentApplier()
                        applier.apply_chart_components(data=data)

                        mock_shading.assert_called_once()

    def test_no_dawn_dusk_shading_for_non_temperature(self) -> None:
        """Test no dawn/dusk shading for non-temperature charts."""
        mock_ax = MagicMock()
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
            chart_title="Test",
            y_label="Y",
            station_icao=None,
            value_formatter=None,
            add_kalshi_strike_lines_func=MagicMock(),
            add_comprehensive_temperature_labels_func=MagicMock(),
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_component_applier.add_vertical_line_annotations"):
            with patch("common.chart_generator_helpers.chart_component_applier.add_dawn_dusk_shading") as mock_shading:
                with patch("common.chart_generator_helpers.chart_component_applier.AxesLimitsConfigurator"):
                    with patch("common.chart_generator_helpers.chart_component_applier.ChartTitlesLabelsApplier"):
                        applier = ChartComponentApplier()
                        applier.apply_chart_components(data=data)

                        mock_shading.assert_not_called()

    def test_adds_kalshi_strikes_for_temperature(self) -> None:
        """Test adds Kalshi strike lines for temperature charts."""
        mock_ax = MagicMock()
        mock_add_strikes = MagicMock()
        mock_add_labels = MagicMock()
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
            kalshi_strikes=[72.0, 75.0],
            chart_title="Temperature",
            y_label="",
            station_icao="KMIA",
            value_formatter=None,
            add_kalshi_strike_lines_func=mock_add_strikes,
            add_comprehensive_temperature_labels_func=mock_add_labels,
            mdates=MagicMock(),
        )

        with patch("common.chart_generator_helpers.chart_component_applier.add_vertical_line_annotations"):
            with patch("common.chart_generator_helpers.chart_component_applier.add_dawn_dusk_shading"):
                with patch("common.chart_generator_helpers.chart_component_applier.AxesLimitsConfigurator"):
                    with patch("common.chart_generator_helpers.chart_component_applier.ChartTitlesLabelsApplier"):
                        applier = ChartComponentApplier()
                        applier.apply_chart_components(data=data)

                        mock_add_strikes.assert_called_once_with(mock_ax, [72.0, 75.0])
                        mock_add_labels.assert_called_once()


class TestChartComponentApplierApplyStatisticsAndFormatting:
    """Tests for apply_statistics_and_formatting method."""

    def test_adds_statistics_text(self) -> None:
        """Test adds statistics text."""
        mock_ax = MagicMock()
        mock_format_y = MagicMock()
        mock_formatter = MagicMock()
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = StatisticsFormattingConfig(
            ax=mock_ax,
            stats=stats,
            values=[30.0, 50.0, 70.0],
            value_formatter=mock_formatter,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=False,
            format_y_axis_func=mock_format_y,
        )

        with patch("common.chart_generator_helpers.chart_component_applier.StatisticsTextAdder") as mock_adder_cls:
            mock_adder = MagicMock()
            mock_adder_cls.return_value = mock_adder

            applier = ChartComponentApplier()
            applier.apply_statistics_and_formatting(config=config)

            mock_adder.add_statistics_text.assert_called_once()
            mock_format_y.assert_called_once_with(ax=mock_ax, formatter=mock_formatter)

    def test_calls_format_y_axis(self) -> None:
        """Test calls format_y_axis_func."""
        mock_ax = MagicMock()
        mock_format_y = MagicMock()
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        config = StatisticsFormattingConfig(
            ax=mock_ax,
            stats=stats,
            values=[30.0, 50.0, 70.0],
            value_formatter=None,
            is_price_chart=True,
            is_temperature_chart=False,
            is_pnl_chart=False,
            format_y_axis_func=mock_format_y,
        )

        with patch("common.chart_generator_helpers.chart_component_applier.StatisticsTextAdder"):
            applier = ChartComponentApplier()
            applier.apply_statistics_and_formatting(config=config)

            mock_format_y.assert_called_once_with(ax=mock_ax, formatter=None)
