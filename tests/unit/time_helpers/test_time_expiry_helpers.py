from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.common.time_helpers import expiry as expiry_module
from src.common.time_helpers.expiry import (
    DateTimeExpiry,
    calculate_time_to_expiry_years,
    find_closest_expiry,
    format_time_key,
    get_datetime_from_time_point,
    get_fixed_time_point,
    get_time_from_epoch,
    is_market_expired,
    match_expiries_exactly,
    parse_iso_datetime,
    validate_expiry_hour,
)


def reset_clamp_flag():
    expiry_module._PRE_EPOCH_CLAMP_LOGGED = False  # type: ignore[attr-defined]


def test_validate_expiry_hour_logs_when_unexpected(caplog):
    dt = datetime(2024, 8, 20, 9, tzinfo=timezone.utc)
    with caplog.at_level("WARNING"):
        assert not validate_expiry_hour(dt, expected_hour=8)
    assert "Unexpected expiry hour" in caplog.text
    caplog.clear()
    assert validate_expiry_hour(dt, expected_hour=None)


def test_time_to_expiry_years_and_epoch_clamping():
    now = datetime(2024, 8, 20, tzinfo=timezone.utc)
    later = now + timedelta(days=365)
    years = calculate_time_to_expiry_years(now, later)
    assert pytest.approx(years, rel=1e-3) == 1.0

    reset_clamp_flag()
    pre_epoch = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert get_time_from_epoch(pre_epoch) == 0.0

    point = 0.5
    dt = get_datetime_from_time_point(point)
    assert isinstance(dt, datetime)
    assert pytest.approx(get_time_from_epoch(dt), rel=1e-6) == point


def test_parse_iso_datetime_requires_iso(caplog):
    reset_clamp_flag()
    iso = "2025-02-01T08:00:00Z"
    dt, time_point = parse_iso_datetime(iso)
    assert dt.isoformat().startswith("2025-02-01T08:00:00")
    assert time_point > 0

    non_iso = "20AUG25"
    with caplog.at_level("ERROR"):
        assert parse_iso_datetime(non_iso) is None
    assert "Failed to parse ISO expiry" in caplog.text

    assert parse_iso_datetime("BAD") is None

    assert get_fixed_time_point(iso) == time_point
    assert format_time_key(time_point) == f"{time_point:.6f}"
    assert format_time_key(None) is None


def test_is_market_expired():
    future = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    assert not is_market_expired(future)
    assert is_market_expired("invalid")


def test_datetime_expiry_comparisons():
    dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
    expiry_dt = DateTimeExpiry(dt)
    expiry_str = DateTimeExpiry("2025-01-10T00:00:00Z")
    expiry_point = DateTimeExpiry(expiry_dt.time_point)

    assert expiry_dt == expiry_str == expiry_point
    assert not (expiry_dt < dt - timedelta(days=1))
    assert expiry_dt > dt - timedelta(days=1)
    assert expiry_dt >= expiry_point
    assert str(expiry_dt).startswith("2025-")


def test_find_closest_and_match_expiries():
    expiries = [
        "2025-01-05T00:00:00Z",
        DateTimeExpiry("2025-01-10T00:00:00Z"),
        get_time_from_epoch(datetime(2025, 1, 15, tzinfo=timezone.utc)),
        "bad",
    ]
    closest = find_closest_expiry(expiries, "2025-01-12T00:00:00Z")
    assert closest == expiries[1]

    matches = match_expiries_exactly(expiries, "2025-01-10T00:00:00Z")
    assert matches == [expiries[1]]

    assert find_closest_expiry([], "2025-01-01T00:00:00Z") is None
    assert match_expiries_exactly([], "2025-01-01T00:00:00Z") == []
