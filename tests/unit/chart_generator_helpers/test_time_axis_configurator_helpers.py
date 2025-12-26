"""Tests for chart_generator_helpers.time_axis_configurator_helpers module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator_helpers.time_axis_configurator_helpers import (
    DEFAULT_TICK_INTERVAL_MINUTES_BASE,
    DEFAULT_TICK_INTERVAL_MINUTES_FAR,
    DEFAULT_TICK_INTERVAL_MINUTES_NEAR,
    configure_default_axis,
    configure_price_axis_locators,
    configure_temperature_axis,
)


class TestConstants:
    """Tests for module constants."""

    def test_default_tick_interval_base(self) -> None:
        """Test default tick interval base constant."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_BASE == 10

    def test_default_tick_interval_near(self) -> None:
        """Test default tick interval near constant."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_NEAR == 30

    def test_default_tick_interval_far(self) -> None:
        """Test default tick interval far constant."""
        assert DEFAULT_TICK_INTERVAL_MINUTES_FAR == 120


class TestConfigureTemperatureAxis:
    """Tests for configure_temperature_axis function."""

    def test_sets_hourly_locator(self) -> None:
        """Test sets hourly locator."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        configure_temperature_axis(mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt)

        mock_mdates.HourLocator.assert_called_once_with(interval=1)
        mock_ax.xaxis.set_major_locator.assert_called_once()

    def test_sets_date_formatter(self) -> None:
        """Test sets date formatter."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        configure_temperature_axis(mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt)

        mock_mdates.DateFormatter.assert_called_once_with("%H:%M")

    def test_sets_empty_xlabel(self) -> None:
        """Test sets empty x-axis label."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        configure_temperature_axis(mock_ax, timestamps, mdates=mock_mdates, plt=mock_plt)

        mock_ax.set_xlabel.assert_called_once_with("")


class TestConfigureDefaultAxis:
    """Tests for configure_default_axis function."""

    def test_short_range_uses_base_interval(self) -> None:
        """Test short range uses base interval."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "min_bucket_hours_near": 4,
                    "min_bucket_hours_mid": 8,
                },
                "time_limits": {"seconds_per_minute": 60},
            }

            configure_default_axis(mock_ax, timestamps, time_range_hours=0.5, mdates=mock_mdates, plt=mock_plt)

        mock_mdates.MinuteLocator.assert_called()

    def test_medium_range_uses_near_interval(self) -> None:
        """Test medium range uses near interval."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "min_bucket_hours_near": 4,
                    "min_bucket_hours_mid": 8,
                },
                "time_limits": {"seconds_per_minute": 60},
            }

            configure_default_axis(mock_ax, timestamps, time_range_hours=2, mdates=mock_mdates, plt=mock_plt)

        mock_mdates.MinuteLocator.assert_called()

    def test_long_range_uses_hour_locator(self) -> None:
        """Test long range uses hour locator."""
        mock_ax = MagicMock()
        mock_mdates = MagicMock()
        mock_plt = MagicMock()
        timestamps = [datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "min_bucket_hours_near": 4,
                    "min_bucket_hours_mid": 8,
                },
                "time_limits": {"seconds_per_minute": 60},
            }

            configure_default_axis(mock_ax, timestamps, time_range_hours=6, mdates=mock_mdates, plt=mock_plt)

        mock_mdates.HourLocator.assert_called()


class TestConfigurePriceAxisLocators:
    """Tests for configure_price_axis_locators function."""

    def test_short_range_2_hour_interval(self) -> None:
        """Test short range uses 2 hour interval."""
        mock_mdates = MagicMock()
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "bucket_hours_far_2": 24,
                    "bucket_hours_far_3": 48,
                    "bucket_hours_far_4": 168,
                },
            }

            major, formatter, minor = configure_price_axis_locators(total_hours=12, start=start, end=end, mdates=mock_mdates)

        mock_mdates.HourLocator.assert_called()

    def test_medium_range_4_hour_interval(self) -> None:
        """Test medium range uses 4 hour interval."""
        mock_mdates = MagicMock()
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "bucket_hours_far_2": 24,
                    "bucket_hours_far_3": 48,
                    "bucket_hours_far_4": 168,
                },
            }

            major, formatter, minor = configure_price_axis_locators(total_hours=36, start=start, end=end, mdates=mock_mdates)

        mock_mdates.HourLocator.assert_called()

    def test_long_range_day_interval(self) -> None:
        """Test long range uses day interval."""
        mock_mdates = MagicMock()
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 1, 0, 0, 0, tzinfo=timezone.utc)

        with patch("common.config_loader.load_config") as mock_config:
            mock_config.return_value = {
                "chart_generation": {
                    "bucket_hours_far_2": 24,
                    "bucket_hours_far_3": 48,
                    "bucket_hours_far_4": 168,
                },
            }

            major, formatter, minor = configure_price_axis_locators(total_hours=744, start=start, end=end, mdates=mock_mdates)

        mock_mdates.DayLocator.assert_called()
