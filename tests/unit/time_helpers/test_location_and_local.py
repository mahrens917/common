from datetime import datetime, timezone

import pytest

from src.common.time_helpers.location import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    _get_timezone_heuristic,
    get_timezone_from_coordinates,
)
from src.common.time_utils.local import calculate_local_midnight_utc, is_after_local_midnight


def test_get_timezone_from_coordinates_validates_bounds():
    with pytest.raises(ValueError):
        get_timezone_from_coordinates(MIN_LATITUDE - 1, 0)
    with pytest.raises(ValueError):
        get_timezone_from_coordinates(0, MAX_LONGITUDE + 1)


def test_timezone_heuristic_and_import_fallback(monkeypatch):
    # Force ImportError path
    def fake_import(name, *args, **kwargs):
        if name == "timezonefinder":
            raise ImportError()
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    tz = get_timezone_from_coordinates(40, -74)
    assert tz in {"America/New_York", "UTC"}

    # Direct heuristic checks
    assert _get_timezone_heuristic(40, -74) == "America/New_York"
    assert _get_timezone_heuristic(34, -118) == "America/Los_Angeles"
    assert _get_timezone_heuristic(35, 140) == "Asia/Tokyo"
    assert _get_timezone_heuristic(51, 0) == "Europe/London"


def test_local_midnight_and_after_check(monkeypatch):
    now = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)

    # Use a fixed timezone response
    monkeypatch.setattr(
        "src.common.time_helpers.location.get_timezone_from_coordinates",
        lambda *_args, **_kwargs: "UTC",
    )

    midnight = calculate_local_midnight_utc(0, 0, now)
    assert midnight.hour == 0 and midnight.tzinfo == timezone.utc

    assert is_after_local_midnight(0, 0, now)
    assert is_after_local_midnight(0, 0, datetime(2024, 1, 1, 0, tzinfo=timezone.utc))
