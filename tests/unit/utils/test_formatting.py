"""Tests for common formatting utilities."""

from common.utils.formatting import convert_keys_to_strings, format_duration


def test_format_duration_zero_or_negative():
    assert format_duration(0) == "0s"
    assert format_duration(-5) == "0s"
    assert format_duration("not a number") == "0s"


def test_format_duration_seconds_and_minutes():
    assert format_duration(30) == "30.00s"
    assert format_duration(90) == "1.50m"


def test_format_duration_hours():
    assert format_duration(7200) == "2.00h"


def test_convert_keys_to_strings_with_dict():
    """Convert dictionary keys to strings."""
    data = {1: "a", 2: "b", 3: {4: "c"}}
    result = convert_keys_to_strings(data)
    assert result == {"1": "a", "2": "b", "3": {"4": "c"}}


def test_convert_keys_to_strings_with_list():
    """Convert keys in dictionaries within lists."""
    data = [{1: "a"}, {2: "b"}]
    result = convert_keys_to_strings(data)
    assert result == [{"1": "a"}, {"2": "b"}]


def test_convert_keys_to_strings_with_primitives():
    """Return primitives unchanged."""
    assert convert_keys_to_strings("string") == "string"
    assert convert_keys_to_strings(123) == 123
    assert convert_keys_to_strings(None) is None
