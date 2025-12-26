"""Tests for chart_generator_helpers.chart_data_preparer module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator_helpers.chart_data_preparer import ChartDataPreparer
from common.chart_generator_helpers.config import ChartPreparationData


class TestChartDataPreparerInit:
    """Tests for ChartDataPreparer initialization."""

    def test_stores_colors(self) -> None:
        """Test stores color configuration."""
        preparer = ChartDataPreparer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
        )

        assert preparer.primary_color == "blue"
        assert preparer.secondary_color == "gray"
        assert preparer.highlight_color == "red"


class TestChartDataPreparerPrepareAndRenderSeries:
    """Tests for prepare_and_render_series method."""

    def test_returns_four_element_tuple(self) -> None:
        """Test returns tuple with time_context, stats, overlay_result, latest_point."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_np = MagicMock()
        now = datetime.now(tz=timezone.utc)

        data = ChartPreparationData(
            ax=mock_ax,
            timestamps=[now, now],
            values=[50.0, 60.0],
            prediction_timestamps=None,
            prediction_values=None,
            prediction_uncertainties=None,
            station_coordinates=None,
            is_temperature_chart=False,
            is_price_chart=False,
            is_pnl_chart=False,
            line_color=None,
            value_formatter=None,
            mdates=mock_mdates,
            np=mock_np,
        )

        with patch("common.chart_generator_helpers.chart_data_preparer.TimeContextBuilder") as mock_time_builder:
            mock_time_ctx = MagicMock()
            mock_time_ctx.naive = [now, now]
            mock_time_ctx.prediction = None
            mock_time_builder.return_value.prepare_time_context.return_value = mock_time_ctx

            with patch("common.chart_generator_helpers.chart_data_preparer.SeriesStatisticsCalculator") as mock_stats:
                mock_stats_result = MagicMock()
                mock_stats.return_value.compute_series_statistics.return_value = mock_stats_result

                with patch("common.chart_generator_helpers.chart_data_preparer.PrimarySeriesRenderer") as mock_renderer:
                    mock_renderer.return_value.render_primary_series.return_value = (now, 60.0)

                    with patch("common.chart_generator_helpers.chart_data_preparer.render_prediction_overlay_if_needed") as mock_overlay:
                        mock_overlay_result = MagicMock()
                        mock_overlay.return_value = mock_overlay_result

                        preparer = ChartDataPreparer(
                            primary_color="blue",
                            secondary_color="gray",
                            highlight_color="red",
                        )
                        result = preparer.prepare_and_render_series(
                            ax=mock_ax,
                            timestamps=[now, now],
                            values=[50.0, 60.0],
                            data=data,
                        )

                        assert len(result) == 4
                        assert result[0] is mock_time_ctx
                        assert result[1] is mock_stats_result
                        assert result[2] is mock_overlay_result
                        assert result[3] == (now, 60.0)

    def test_uses_custom_line_color(self) -> None:
        """Test uses custom line color when provided."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_np = MagicMock()
        now = datetime.now(tz=timezone.utc)

        data = ChartPreparationData(
            ax=mock_ax,
            timestamps=[now, now],
            values=[50.0, 60.0],
            prediction_timestamps=None,
            prediction_values=None,
            prediction_uncertainties=None,
            station_coordinates=None,
            is_temperature_chart=False,
            is_price_chart=False,
            is_pnl_chart=False,
            line_color="green",  # Custom color
            value_formatter=None,
            mdates=mock_mdates,
            np=mock_np,
        )

        with patch("common.chart_generator_helpers.chart_data_preparer.TimeContextBuilder") as mock_time_builder:
            mock_time_ctx = MagicMock()
            mock_time_ctx.naive = [now, now]
            mock_time_ctx.prediction = None
            mock_time_builder.return_value.prepare_time_context.return_value = mock_time_ctx

            with patch("common.chart_generator_helpers.chart_data_preparer.SeriesStatisticsCalculator") as mock_stats:
                mock_stats.return_value.compute_series_statistics.return_value = MagicMock()

                with patch("common.chart_generator_helpers.chart_data_preparer.PrimarySeriesRenderer") as mock_renderer:
                    mock_renderer.return_value.render_primary_series.return_value = None

                    with patch("common.chart_generator_helpers.chart_data_preparer.render_prediction_overlay_if_needed"):
                        preparer = ChartDataPreparer(
                            primary_color="blue",
                            secondary_color="gray",
                            highlight_color="red",
                        )
                        preparer.prepare_and_render_series(
                            ax=mock_ax,
                            timestamps=[now, now],
                            values=[50.0, 60.0],
                            data=data,
                        )

                        call_args = mock_renderer.return_value.render_primary_series.call_args
                        config = call_args[1]["config"]
                        assert config.plot_color == "green"


class TestChartDataPreparerAnnotateLatestIfApplicable:
    """Tests for _annotate_latest_if_applicable method."""

    def test_skips_when_latest_point_none(self) -> None:
        """Test skips annotation when latest_point is None."""
        preparer = ChartDataPreparer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
        )
        mock_ax = MagicMock()

        with patch("common.chart_generator_helpers.chart_data_preparer.LatestValueAnnotator") as mock_annotator:
            preparer._annotate_latest_if_applicable(
                ax=mock_ax,
                latest_point=None,
                formatter=None,
                is_pnl_chart=False,
                mdates=MagicMock(),
            )

            mock_annotator.assert_not_called()

    def test_skips_for_pnl_chart(self) -> None:
        """Test skips annotation for PnL charts."""
        preparer = ChartDataPreparer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
        )
        mock_ax = MagicMock()
        now = datetime.now(tz=timezone.utc)

        with patch("common.chart_generator_helpers.chart_data_preparer.LatestValueAnnotator") as mock_annotator:
            preparer._annotate_latest_if_applicable(
                ax=mock_ax,
                latest_point=(now, 50.0),
                formatter=None,
                is_pnl_chart=True,
                mdates=MagicMock(),
            )

            mock_annotator.assert_not_called()

    def test_annotates_when_applicable(self) -> None:
        """Test annotates latest value when applicable."""
        preparer = ChartDataPreparer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
        )
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        now = datetime.now(tz=timezone.utc)

        with patch("common.chart_generator_helpers.chart_data_preparer.LatestValueAnnotator") as mock_annotator_cls:
            mock_annotator = MagicMock()
            mock_annotator_cls.return_value = mock_annotator

            preparer._annotate_latest_if_applicable(
                ax=mock_ax,
                latest_point=(now, 75.5),
                formatter=lambda x: f"{x}°F",
                is_pnl_chart=False,
                mdates=mock_mdates,
            )

            mock_annotator_cls.assert_called_once_with(
                primary_color="blue",
                highlight_color="red",
            )
            mock_annotator.annotate_latest_value.assert_called_once()
