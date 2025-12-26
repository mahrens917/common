"""Tests for chart_generator_helpers.time_context_builder module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from common.chart_generator_helpers.time_context_builder import TimeContextBuilder


class TestTimeContextBuilderInit:
    """Tests for TimeContextBuilder initialization."""

    def test_creates_instance(self) -> None:
        """Test creates instance."""
        builder = TimeContextBuilder()
        assert builder is not None


class TestTimeContextBuilderPrepareTimeContext:
    """Tests for prepare_time_context method."""

    def test_returns_chart_time_context(self) -> None:
        """Test returns ChartTimeContext object."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now, now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=None,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result is not None
                assert hasattr(result, "naive")
                assert hasattr(result, "prediction")
                assert hasattr(result, "axis")

    def test_sets_naive_timestamps(self) -> None:
        """Test sets naive timestamps."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        naive_timestamps = [now.replace(tzinfo=None)]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = naive_timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = naive_timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=None,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result.naive == naive_timestamps

    def test_sets_prediction_none_when_not_provided(self) -> None:
        """Test sets prediction to None when not provided."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=None,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result.prediction is None

    def test_sets_prediction_when_provided(self) -> None:
        """Test sets prediction timestamps when provided."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        pred_timestamps = [now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.side_effect = [timestamps, pred_timestamps]
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps + pred_timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=pred_timestamps,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result.prediction == pred_timestamps

    def test_localizes_for_temperature_chart_with_coordinates(self) -> None:
        """Test localizes timestamps for temperature chart with coordinates."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        coords = (40.7128, -74.0060)

        mock_localized_result = MagicMock()
        mock_localized_result.timestamps = timestamps
        mock_localized_result.timezone = timezone.utc

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps
                with patch("common.chart_generator_helpers.time_context_builder.localize_temperature_timestamps") as mock_localize:
                    mock_localize.return_value = mock_localized_result

                    builder = TimeContextBuilder()
                    result = builder.prepare_time_context(
                        timestamps=timestamps,
                        prediction_timestamps=None,
                        station_coordinates=coords,
                        is_temperature_chart=True,
                    )

                    mock_localize.assert_called_once()
                    assert result.localized == timestamps
                    assert result.local_timezone == timezone.utc

    def test_skips_localization_for_non_temperature_chart(self) -> None:
        """Test skips localization for non-temperature chart."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        coords = (40.7128, -74.0060)

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps
                with patch("common.chart_generator_helpers.time_context_builder.localize_temperature_timestamps") as mock_localize:
                    builder = TimeContextBuilder()
                    result = builder.prepare_time_context(
                        timestamps=timestamps,
                        prediction_timestamps=None,
                        station_coordinates=coords,
                        is_temperature_chart=False,
                    )

                    mock_localize.assert_not_called()
                    assert result.localized is None

    def test_skips_localization_without_coordinates(self) -> None:
        """Test skips localization when coordinates not provided."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps
                with patch("common.chart_generator_helpers.time_context_builder.localize_temperature_timestamps") as mock_localize:
                    builder = TimeContextBuilder()
                    result = builder.prepare_time_context(
                        timestamps=timestamps,
                        prediction_timestamps=None,
                        station_coordinates=None,
                        is_temperature_chart=True,
                    )

                    mock_localize.assert_not_called()
                    assert result.localized is None

    def test_uses_localized_for_plot_when_available(self) -> None:
        """Test uses localized timestamps for plot when available."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        localized = [now]
        coords = (40.7128, -74.0060)

        mock_localized_result = MagicMock()
        mock_localized_result.timestamps = localized
        mock_localized_result.timezone = timezone.utc

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps
                with patch("common.chart_generator_helpers.time_context_builder.localize_temperature_timestamps") as mock_localize:
                    mock_localize.return_value = mock_localized_result

                    builder = TimeContextBuilder()
                    result = builder.prepare_time_context(
                        timestamps=timestamps,
                        prediction_timestamps=None,
                        station_coordinates=coords,
                        is_temperature_chart=True,
                    )

                    assert result.plot == localized

    def test_uses_naive_for_plot_when_not_temperature_chart(self) -> None:
        """Test uses naive timestamps for plot when not temperature chart."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=None,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result.plot == timestamps

    def test_builds_axis_timestamps(self) -> None:
        """Test builds axis timestamps from naive and prediction."""
        now = datetime.now(tz=timezone.utc)
        timestamps = [now]
        axis_timestamps = [now, now]

        with patch("common.chart_generator_helpers.time_context_builder.ensure_naive_timestamps") as mock_naive:
            mock_naive.return_value = timestamps
            with patch("common.chart_generator_helpers.time_context_builder.build_axis_timestamps") as mock_axis:
                mock_axis.return_value = axis_timestamps

                builder = TimeContextBuilder()
                result = builder.prepare_time_context(
                    timestamps=timestamps,
                    prediction_timestamps=None,
                    station_coordinates=None,
                    is_temperature_chart=False,
                )

                assert result.axis == axis_timestamps
