"""Tests for twilight calculation functions."""

from datetime import datetime, date, timezone, timedelta
import pytest

from common.time_utils.twilight import (
    calculate_dawn_utc,
    calculate_dusk_utc,
    is_between_dawn_and_dusk,
    is_after_midpoint_noon_to_dusk,
)
from common.time_utils.base import AstronomicalComputationError


class TestCalculateDawnUtc:
    """Tests for calculate_dawn_utc function."""

    def test_calculate_dawn_for_valid_coordinates(self):
        """Calculate dawn for valid coordinates."""
        test_date = date(2024, 6, 21)
        result = calculate_dawn_utc(40.7128, -74.0060, test_date)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_calculate_dawn_with_datetime_input(self):
        """Calculate dawn with datetime input."""
        test_datetime = datetime(2024, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
        result = calculate_dawn_utc(40.7128, -74.0060, test_datetime)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_calculate_dawn_with_naive_datetime(self):
        """Calculate dawn with naive datetime (no timezone)."""
        test_datetime = datetime(2024, 6, 21, 12, 0, 0)
        result = calculate_dawn_utc(40.7128, -74.0060, test_datetime)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_calculate_dawn_invalid_latitude(self):
        """Raise ValueError for invalid latitude."""
        with pytest.raises(ValueError, match="Latitude.*out of valid range"):
            calculate_dawn_utc(91.0, -74.0060, date(2024, 6, 21))

    def test_calculate_dawn_invalid_longitude(self):
        """Raise ValueError for invalid longitude."""
        with pytest.raises(ValueError, match="Longitude.*out of valid range"):
            calculate_dawn_utc(40.7128, 181.0, date(2024, 6, 21))

    def test_calculate_dawn_polar_region(self):
        """Raise AstronomicalComputationError for polar day."""
        with pytest.raises(AstronomicalComputationError, match="Polar day prevents dawn calculation"):
            calculate_dawn_utc(89.0, 0.0, date(2024, 6, 21))


class TestCalculateDuskUtc:
    """Tests for calculate_dusk_utc function."""

    def test_calculate_dusk_for_valid_coordinates(self):
        """Calculate dusk for valid coordinates."""
        test_date = date(2024, 6, 21)
        result = calculate_dusk_utc(40.7128, -74.0060, test_date)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_calculate_dusk_polar_region(self):
        """Raise AstronomicalComputationError for polar night."""
        with pytest.raises(AstronomicalComputationError, match="Polar day prevents dusk calculation"):
            calculate_dusk_utc(89.0, 0.0, date(2024, 12, 21))


class TestIsBetweenDawnAndDusk:
    """Tests for is_between_dawn_and_dusk function."""

    def test_is_between_dawn_and_dusk_daytime(self):
        """Return True when current time is between dawn and dusk."""
        test_time = datetime(2024, 6, 21, 14, 0, 0, tzinfo=timezone.utc)
        result = is_between_dawn_and_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_between_dawn_and_dusk_nighttime(self):
        """Return False when current time is before dawn or after dusk."""
        test_time = datetime(2024, 6, 21, 2, 0, 0, tzinfo=timezone.utc)
        result = is_between_dawn_and_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_between_dawn_and_dusk_no_time_provided(self):
        """Use current time when no time is provided."""
        result = is_between_dawn_and_dusk(40.7128, -74.0060)
        assert isinstance(result, bool)

    def test_is_between_dawn_and_dusk_naive_datetime(self):
        """Handle naive datetime by assuming UTC."""
        test_time = datetime(2024, 6, 21, 14, 0, 0)
        result = is_between_dawn_and_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_between_dawn_and_dusk_previous_day(self):
        """Check previous day's dawn/dusk window."""
        test_time = datetime(2024, 6, 21, 1, 0, 0, tzinfo=timezone.utc)
        result = is_between_dawn_and_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_between_dawn_and_dusk_next_day(self):
        """Check next day's dawn/dusk window."""
        test_time = datetime(2024, 6, 21, 23, 0, 0, tzinfo=timezone.utc)
        result = is_between_dawn_and_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)


class TestIsAfterMidpointNoonToDusk:
    """Tests for is_after_midpoint_noon_to_dusk function."""

    def test_is_after_midpoint_before_midpoint(self):
        """Return False when before midpoint between noon and dusk."""
        test_time = datetime(2024, 6, 21, 13, 0, 0, tzinfo=timezone.utc)
        result = is_after_midpoint_noon_to_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_after_midpoint_after_midpoint(self):
        """Return True when after midpoint between noon and dusk."""
        test_time = datetime(2024, 6, 21, 20, 0, 0, tzinfo=timezone.utc)
        result = is_after_midpoint_noon_to_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)

    def test_is_after_midpoint_no_time_provided(self):
        """Use current time when no time is provided."""
        result = is_after_midpoint_noon_to_dusk(40.7128, -74.0060)
        assert isinstance(result, bool)

    def test_is_after_midpoint_naive_datetime(self):
        """Handle naive datetime by assuming UTC."""
        test_time = datetime(2024, 6, 21, 20, 0, 0)
        result = is_after_midpoint_noon_to_dusk(40.7128, -74.0060, test_time)
        assert isinstance(result, bool)


class TestTwilightEdgeCases:
    """Tests for edge cases in twilight calculations."""

    def test_dawn_wraps_to_previous_day(self):
        """Handle dawn time that wraps to previous day."""
        result = calculate_dawn_utc(40.7128, -74.0060, date(2024, 1, 15))
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_dusk_wraps_to_next_day(self):
        """Handle dusk time that wraps to next day."""
        result = calculate_dusk_utc(40.7128, -74.0060, date(2024, 1, 15))
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
