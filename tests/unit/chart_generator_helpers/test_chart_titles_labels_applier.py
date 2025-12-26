"""Tests for chart_generator_helpers.chart_titles_labels_applier module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from common.chart_generator.contexts import ChartStatistics, ChartTimeContext
from common.chart_generator_helpers.chart_titles_labels_applier import (
    ChartTitlesLabelsApplier,
)
from common.chart_generator_helpers.config import ChartTitlesLabelsData


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


class TestChartTitlesLabelsApplierApplyTitlesAndLabels:
    """Tests for apply_titles_and_labels method."""

    def test_sets_title(self) -> None:
        """Test sets chart title."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Test Chart Title",
            y_label="Y Axis",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            station_icao=None,
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_title.assert_called_once()
        call_args = mock_ax.set_title.call_args
        assert call_args[0][0] == "Test Chart Title"

    def test_sets_white_background(self) -> None:
        """Test sets white background color."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Test",
            y_label="Y Axis",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            station_icao=None,
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_facecolor.assert_called_once_with("white")

    def test_temperature_chart_y_axis_on_right(self) -> None:
        """Test temperature chart has Y axis on right."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        mock_yaxis = MagicMock()
        mock_ax.yaxis = mock_yaxis
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=70, max_value=75, mean_value=72)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Temperature",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            station_icao="KMIA",
        )

        applier.apply_titles_and_labels(data=data)

        mock_yaxis.tick_right.assert_called_once()
        mock_yaxis.set_label_position.assert_called_once_with("right")

    def test_temperature_chart_sets_tick_labels(self) -> None:
        """Test temperature chart sets tick labels with degree symbol."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        mock_yaxis = MagicMock()
        mock_ax.yaxis = mock_yaxis
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=70, max_value=73, mean_value=71)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Temperature",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            station_icao="KMIA",
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_yticks.assert_called_once()
        tick_values = mock_ax.set_yticks.call_args[0][0]
        assert tick_values == [70, 71, 72, 73]

        mock_ax.set_yticklabels.assert_called_once()
        labels = mock_ax.set_yticklabels.call_args[0][0]
        assert labels == ["70°F", "71°F", "72°F", "73°F"]

    def test_temperature_chart_sets_timestamp_xlabel(self) -> None:
        """Test temperature chart sets Timestamp as x-label."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        mock_yaxis = MagicMock()
        mock_ax.yaxis = mock_yaxis
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=70, max_value=75, mean_value=72)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Temperature",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            station_icao="KMIA",
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_xlabel.assert_called_once_with("Timestamp")

    def test_pnl_chart_labels(self) -> None:
        """Test PnL chart sets Day and PnL labels."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=-100, max_value=200, mean_value=50)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="PnL Chart",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=True,
            station_icao=None,
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_xlabel.assert_called_once_with("Day")
        mock_ax.set_ylabel.assert_called_once_with("PnL")

    def test_regular_chart_labels(self) -> None:
        """Test regular chart sets Timestamp and custom y-label."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Regular Chart",
            y_label="Custom Y Label",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            station_icao=None,
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_xlabel.assert_called_once_with("Timestamp")
        mock_ax.set_ylabel.assert_called_once_with("Custom Y Label", fontsize=12)

    def test_regular_chart_no_ylabel_when_empty(self) -> None:
        """Test regular chart does not set y-label when empty."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Regular Chart",
            y_label="",  # Empty string
            stats=stats,
            time_context=time_context,
            is_temperature_chart=False,
            is_pnl_chart=False,
            station_icao=None,
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_xlabel.assert_called_once_with("Timestamp")
        mock_ax.set_ylabel.assert_not_called()

    def test_temperature_handles_equal_min_max(self) -> None:
        """Test temperature chart handles equal min and max values."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        mock_yaxis = MagicMock()
        mock_ax.yaxis = mock_yaxis
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        stats = ChartStatistics(min_value=72, max_value=72, mean_value=72)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Temperature",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            station_icao="KMIA",
        )

        applier.apply_titles_and_labels(data=data)

        mock_ax.set_yticks.assert_called_once()
        tick_values = mock_ax.set_yticks.call_args[0][0]
        assert tick_values == [72]

    def test_temperature_skips_ticks_when_inverted(self) -> None:
        """Test temperature chart skips ticks when min > max."""
        applier = ChartTitlesLabelsApplier()
        mock_ax = MagicMock()
        mock_yaxis = MagicMock()
        mock_ax.yaxis = mock_yaxis
        now = datetime.now(tz=timezone.utc)
        time_context = make_time_context([now])
        # Stats where int(min) > int(max) - would create invalid range
        stats = ChartStatistics(min_value=75.9, max_value=70.1, mean_value=72)

        data = ChartTitlesLabelsData(
            ax=mock_ax,
            chart_title="Temperature",
            y_label="",
            stats=stats,
            time_context=time_context,
            is_temperature_chart=True,
            is_pnl_chart=False,
            station_icao="KMIA",
        )

        applier.apply_titles_and_labels(data=data)

        # Should not call set_yticks when min_temp > max_temp
        mock_ax.set_yticks.assert_not_called()
