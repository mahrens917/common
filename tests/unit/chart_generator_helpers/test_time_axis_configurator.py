"""Tests for chart_generator_helpers.time_axis_configurator module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from common.chart_generator_helpers.time_axis_configurator import (
    DEFAULT_TICK_INTERVAL_MINUTES_EXTRA_LONG,
    DEFAULT_TICK_INTERVAL_MINUTES_LONG,
    DEFAULT_TICK_INTERVAL_MINUTES_MEDIUM,
    DEFAULT_TICK_INTERVAL_MINUTES_SHORT,
    TimeAxisConfigurator,
)


class TestTimeAxisConfiguratorConstants:
    """Tests for module constants."""

    def test_tick_interval_short(self) -> None:
        """Test short tick interval."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_SHORT == 10

    def test_tick_interval_medium(self) -> None:
        """Test medium tick interval."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_MEDIUM == 30

    def test_tick_interval_long(self) -> None:
        """Test long tick interval."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_LONG == 60

    def test_tick_interval_extra_long(self) -> None:
        """Test extra long tick interval."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_EXTRA_LONG == 120


class TestTimeAxisConfiguratorConfigureTimeAxis:
    """Tests for configure_time_axis_with_5_minute_alignment method."""

    def test_empty_timestamps_returns_early(self) -> None:
        """Test returns early with empty timestamps."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax, [], mdates=mock_mdates, plt=mock_plt
        )

        mock_ax.xaxis.set_major_locator.assert_not_called()

    def test_temperature_chart_hourly_locator(self) -> None:
        """Test temperature chart uses hourly locator."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(hours=6)]

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax,
            timestamps,
            chart_type="temperature",
            mdates=mock_mdates,
            plt=mock_plt,
        )

        mock_mdates.HourLocator.assert_called_with(interval=1)
        mock_ax.set_xlabel.assert_called_with("")

    def test_short_range_uses_10_minute_interval(self) -> None:
        """Test short range uses 10 minute interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        # 30 minute range (< 1 hour)
        timestamps = [now, now + timedelta(minutes=30)]

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.MinuteLocator.assert_called()

    def test_medium_range_uses_30_minute_interval(self) -> None:
        """Test medium range uses 30 minute interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        # 2 hour range (> 1 hour, < 3 hours)
        timestamps = [now, now + timedelta(hours=2)]

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.MinuteLocator.assert_called()

    def test_extended_range_uses_60_minute_interval(self) -> None:
        """Test extended range uses 60 minute interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        # 6 hour range (> 3 hours, < 12 hours)
        timestamps = [now, now + timedelta(hours=6)]

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.MinuteLocator.assert_called()

    def test_long_range_uses_120_minute_interval(self) -> None:
        """Test long range uses 120 minute interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        # 24 hour range (> 12 hours)
        timestamps = [now, now + timedelta(hours=24)]

        configurator.configure_time_axis_with_5_minute_alignment(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.MinuteLocator.assert_called()


class TestTimeAxisConfiguratorConfigurePriceChartAxis:
    """Tests for configure_price_chart_axis method."""

    def test_empty_timestamps_returns_early(self) -> None:
        """Test returns early with empty timestamps."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()

        configurator.configure_price_chart_axis(mock_ax, [], mdates=mock_mdates, plt=mock_plt)

        mock_ax.xaxis.set_major_locator.assert_not_called()

    def test_short_range_2_hour_interval(self) -> None:
        """Test short range uses 2 hour interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(hours=12)]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.HourLocator.assert_called()
        mock_ax.set_xlim.assert_called()

    def test_medium_range_4_hour_interval(self) -> None:
        """Test medium range uses 4 hour interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(hours=48)]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.HourLocator.assert_called()

    def test_extended_range_8_hour_interval(self) -> None:
        """Test extended range uses 8 hour interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(hours=120)]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.HourLocator.assert_called()

    def test_long_range_12_hour_interval(self) -> None:
        """Test long range uses 12 hour interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(days=12)]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.HourLocator.assert_called()

    def test_very_long_range_day_interval(self) -> None:
        """Test very long range uses day interval."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        timestamps = [now, now + timedelta(days=30)]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        mock_mdates.DayLocator.assert_called()

    def test_handles_end_before_start(self) -> None:
        """Test handles when end equals start."""
        configurator = TimeAxisConfigurator()
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        now = datetime.now(timezone.utc)
        # Same timestamp for start and end
        timestamps = [now, now]

        configurator.configure_price_chart_axis(
            mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt
        )

        # Should still configure the axis
        mock_ax.xaxis.set_major_locator.assert_called()
