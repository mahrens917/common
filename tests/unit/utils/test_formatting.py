"""Tests for common formatting utilities."""

from common.utils.formatting import format_duration


def test_format_duration_zero_or_negative():
    assert format_duration(0) == "0s"
    assert format_duration(-5) == "0s"
    assert format_duration("not a number") == "0s"


def test_format_duration_seconds_and_minutes():
    assert format_duration(30) == "30.00s"
    assert format_duration(90) == "1.50m"


def test_format_duration_hours():
    assert format_duration(7200) == "2.00h"
