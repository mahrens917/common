"""Unit tests for moon_phase_calculator."""

from datetime import datetime as real_datetime_class
from datetime import timedelta
from datetime import timezone as real_timezone
from unittest.mock import MagicMock, patch  # Import MagicMock

import pytest

from src.common.optimized_status_reporter_helpers.moon_phase_calculator import (
    MoonPhaseCalculator,
)


class TestMoonPhaseCalculator:
    """Tests for MoonPhaseCalculator."""

    KNOWN_NEW_MOON = real_datetime_class(2024, 1, 11, 11, 57, tzinfo=real_timezone.utc)
    LUNAR_CYCLE_DAYS = 29.53059
    DAY_SECONDS = 24 * 3600

    @pytest.mark.parametrize(
        "days_offset_td, expected_emoji",
        [
            # New Moon (0 days from known new moon)
            (timedelta(seconds=1), "🌑"),  # Slightly after new moon
            # Waxing Crescent (~3.69 days)
            (timedelta(days=3.7), "🌒"),
            # First Quarter (~7.38 days)
            (timedelta(days=7.4), "🌓"),
            # Waxing Gibbous (~11.07 days)
            (timedelta(days=11.1), "🌔"),
            # Full Moon (~14.76 days)
            (timedelta(days=14.8), "🌕"),
            # Waning Gibbous (~18.45 days)
            (timedelta(days=18.5), "🌖"),
            # Last Quarter (~22.14 days)
            (timedelta(days=22.2), "🌗"),
            # Waning Crescent (~25.83 days)
            (timedelta(days=25.9), "🌘"),
            # Another New Moon (full cycle + small offset)
            (timedelta(days=LUNAR_CYCLE_DAYS + 0.1), "🌑"),
        ],
    )
    def test_get_moon_phase_emoji_various_phases(self, days_offset_td, expected_emoji, mocker):
        """Test get_moon_phase_emoji for various points in the lunar cycle."""
        now_mock_dt = self.KNOWN_NEW_MOON + days_offset_td

        # Patch the `datetime` class as it's imported into `moon_phase_calculator`
        mock_datetime_class = mocker.patch(
            "src.common.optimized_status_reporter_helpers.moon_phase_calculator.datetime"
        )

        # Configure the `now()` method of the mocked datetime class
        mock_datetime_class.now.return_value = now_mock_dt

        # Make the mock callable as if it were the datetime constructor
        mock_datetime_class.side_effect = lambda *args, **kwargs: real_datetime_class(
            *args, **kwargs
        )

        # Patch the `timezone` imported into the module to ensure it's the real one
        mocker.patch(
            "src.common.optimized_status_reporter_helpers.moon_phase_calculator.timezone",
            real_timezone,
        )

        result = MoonPhaseCalculator.get_moon_phase_emoji()
        assert result == expected_emoji

    def test_get_moon_phase_emoji_exception_handling(self, mocker):
        """Test get_moon_phase_emoji returns default emoji on exception."""
        # Patch the `datetime` class directly as it's imported into `moon_phase_calculator`
        mock_datetime_class = mocker.patch(
            "src.common.optimized_status_reporter_helpers.moon_phase_calculator.datetime"
        )

        # Force an exception during calculation, e.g., in total_seconds, by making now() return a mock that raises
        mock_datetime_class.now.side_effect = ValueError("Test error")
        mock_datetime_class.side_effect = lambda *args, **kwargs: real_datetime_class(
            *args, **kwargs
        )  # Needed to prevent other errors.

        mocker.patch(
            "src.common.optimized_status_reporter_helpers.moon_phase_calculator.timezone",
            real_timezone,
        )

        result = MoonPhaseCalculator.get_moon_phase_emoji()
        assert result == "🌙"
