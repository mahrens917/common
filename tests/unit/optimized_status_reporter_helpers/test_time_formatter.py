"""Unit tests for time_formatter."""

import math
from datetime import timedelta
from unittest.mock import Mock

import pytest

from common.optimized_status_reporter_helpers.time_formatter import (
    TimeFormatter,
)


class TestTimeFormatter:
    """Tests for TimeFormatter."""

    @pytest.mark.parametrize(
        "value,remainder,unit,remainder_unit,expected",
        [
            (5, 10, "m", "s", "5m 10s"),
            (5, 0, "m", "s", "5m"),
        ],
    )
    def test_format_time_unit(self, value, remainder, unit, remainder_unit, expected):
        """Test _format_time_unit formats correctly."""
        assert TimeFormatter._format_time_unit(value, remainder, unit, remainder_unit) == expected

    @pytest.mark.parametrize(
        "seconds_input,expected",
        [
            (timedelta(seconds=123.45), 123),
            (123, 123),
            (123.45, 123),
            ("123", 123),
            ("123.45", 123),
            ("abc", None),
            (None, None),
            (math.inf, None),
            (math.nan, None),
            (-10, 0),  # Normalized to 0 if negative
        ],
    )
    def test_normalize_seconds(self, seconds_input, expected):
        """Test _normalize_seconds handles various inputs."""
        assert TimeFormatter._normalize_seconds(seconds_input) == expected

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (30, "30s"),
            (59, "59s"),
            (60, "1m"),
            (120, "2m"),
            (121, "2m 1s"),
            (3599, "59m 59s"),
            (3600, "1h"),
            (3661, "1h 1m"),
            (86399, "23h 59m"),
            (86400, "1d"),
            (86401, "1d"),
            (604799, "6d 23h"),
            (604800, "1w"),
            (604801, "1w"),
            (1209600, "2w"),
            (None, "unknown"),
            ("invalid", "unknown"),
            (math.inf, "unknown"),
            (-10, "0s"),  # Should be handled by normalize_seconds
        ],
    )
    def test_humanize_duration(self, seconds, expected):
        """Test humanize_duration with various durations."""
        assert TimeFormatter.humanize_duration(seconds) == expected
