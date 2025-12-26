"""Tests for chart_generator_helpers.astronomical_calculator module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator.contexts import AstronomicalFeatures
from common.chart_generator_helpers.astronomical_calculator import AstronomicalCalculator


class TestAstronomicalCalculator:
    """Tests for AstronomicalCalculator class."""

    def test_init(self) -> None:
        """Test initialization."""
        calculator = AstronomicalCalculator()

        assert calculator.event_processor is not None

    def test_compute_no_coordinates(self) -> None:
        """Test returns empty features when no coordinates."""
        calculator = AstronomicalCalculator()
        timestamps = [datetime(2025, 1, 15, 12, 0, 0)]

        result = calculator.compute_astronomical_features("KJFK", None, timestamps)

        assert result.vertical_lines == []
        assert result.dawn_dusk_periods is None

    def test_compute_with_coordinates(self) -> None:
        """Test computes features with valid coordinates."""
        calculator = AstronomicalCalculator()
        timestamps = [
            datetime(2025, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 1, 15, 23, 59, 59, tzinfo=timezone.utc),
        ]
        coordinates = (40.7128, -74.0060)

        with (
            patch.object(calculator, "_get_local_timezone", return_value=None),
            patch.object(calculator.event_processor, "process_day_astronomical_events"),
        ):
            result = calculator.compute_astronomical_features("KJFK", coordinates, timestamps)

        assert isinstance(result, AstronomicalFeatures)

    def test_compute_handles_exception(self) -> None:
        """Test returns empty features on exception."""
        calculator = AstronomicalCalculator()
        timestamps = [
            datetime(2025, 1, 15, 0, 0, 0),
            datetime(2025, 1, 15, 23, 59, 59),
        ]
        coordinates = (40.7128, -74.0060)

        with patch.object(calculator, "_get_local_timezone", side_effect=RuntimeError("Test error")):
            result = calculator.compute_astronomical_features("KJFK", coordinates, timestamps)

        assert result.vertical_lines == []
        assert result.dawn_dusk_periods is None


class TestGetLocalTimezone:
    """Tests for _get_local_timezone method."""

    def test_returns_timezone(self) -> None:
        """Test returns timezone when lookup succeeds."""
        calculator = AstronomicalCalculator()

        with (
            patch(
                "common.time_utils.get_timezone_from_coordinates",
                return_value="America/New_York",
            ),
            patch("pytz.timezone") as mock_pytz,
        ):
            mock_tz = MagicMock()
            mock_pytz.return_value = mock_tz
            result = calculator._get_local_timezone(40.7128, -74.0060, "KJFK")

        assert result == mock_tz

    def test_returns_none_on_error(self) -> None:
        """Test returns None on lookup error."""
        calculator = AstronomicalCalculator()

        with patch(
            "common.time_utils.get_timezone_from_coordinates",
            side_effect=ValueError("Unknown location"),
        ):
            result = calculator._get_local_timezone(0.0, 0.0, "XXXX")

        assert result is None

    def test_returns_none_on_key_error(self) -> None:
        """Test returns None on KeyError."""
        calculator = AstronomicalCalculator()

        with patch(
            "common.time_utils.get_timezone_from_coordinates",
            side_effect=KeyError("Timezone not found"),
        ):
            result = calculator._get_local_timezone(0.0, 0.0, "XXXX")

        assert result is None
