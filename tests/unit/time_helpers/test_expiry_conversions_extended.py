from datetime import datetime, timedelta, timezone

import pytest

from src.common.time_helpers import expiry
from src.common.time_helpers.expiry_conversions import (
    DERIBIT_EXPIRY_HOUR,
    EPOCH_START,
    calculate_time_to_expiry_years,
    format_time_key,
    get_datetime_from_time_point,
    get_fixed_time_point,
    get_time_from_epoch,
    is_market_expired,
    parse_expiry_datetime,
    parse_iso_datetime,
    resolve_expiry_to_datetime,
    validate_expiry_hour,
)


def test_parse_expiry_datetime_handles_bytes_and_naive():
    dt = parse_expiry_datetime(b"2025-02-01T00:00:00Z")
    assert dt.tzinfo == timezone.utc
    naive = datetime(2025, 2, 1, 0, 0, 0)
    converted = parse_expiry_datetime(naive)
    assert converted.tzinfo == timezone.utc


def test_parse_expiry_datetime_missing_raises():
    with pytest.raises(ValueError):
        parse_expiry_datetime(None)


def test_validate_expiry_hour_matches_and_warns(caplog):
    match_dt = datetime(2025, 2, 1, DERIBIT_EXPIRY_HOUR, 0, tzinfo=timezone.utc)
    assert validate_expiry_hour(match_dt, DERIBIT_EXPIRY_HOUR) is True

    mismatch_dt = match_dt.replace(hour=DERIBIT_EXPIRY_HOUR + 1)
    with caplog.at_level("WARNING"):
        assert validate_expiry_hour(mismatch_dt, DERIBIT_EXPIRY_HOUR) is False
        assert any("Unexpected expiry hour" in msg for msg in caplog.messages)


def test_time_to_expiry_and_epoch_clamping(monkeypatch, caplog):
    # Reset clamp flag in both modules
    monkeypatch.setattr(expiry, "_PRE_EPOCH_CLAMP_LOGGED", False)
    monkeypatch.setattr(
        "src.common.time_helpers.expiry_conversions._PRE_EPOCH_CLAMP_LOGGED",
        False,
        raising=False,
    )

    before_epoch = EPOCH_START - timedelta(days=1)
    with caplog.at_level("WARNING"):
        result = get_time_from_epoch(before_epoch)
        assert result == 0.0  # clamped to epoch
        assert any("clamping to the epoch boundary" in msg for msg in caplog.messages)

    # Subsequent call should not log again once flag set
    caplog.clear()
    _ = get_time_from_epoch(before_epoch)
    assert not caplog.messages


def test_time_point_round_trip():
    future = EPOCH_START + timedelta(days=10)
    time_point = get_time_from_epoch(future)
    assert get_datetime_from_time_point(time_point) == future
    assert calculate_time_to_expiry_years(EPOCH_START, future) > 0


def test_parse_iso_datetime_valid_and_invalid(caplog):
    valid = parse_iso_datetime("2025-02-01T00:00:00+00:00")
    assert valid is not None
    dt, time_point = valid
    assert dt.tzinfo == timezone.utc
    assert time_point >= 0

    with caplog.at_level("ERROR"):
        assert parse_iso_datetime("not-a-date") is None
        assert any("Failed to parse ISO expiry" in msg for msg in caplog.messages)


def test_get_fixed_time_point_and_formatting():
    time_point = get_fixed_time_point("2025-02-01T00:00:00+00:00")
    assert isinstance(time_point, float)
    assert format_time_key(time_point) is not None
    assert format_time_key(None) is None


def test_resolve_expiry_to_datetime_handles_types(monkeypatch):
    naive = datetime(2025, 2, 1, 0, 0, 0)
    resolved = resolve_expiry_to_datetime(naive)
    assert resolved.tzinfo == timezone.utc

    ts = EPOCH_START.timestamp()
    assert resolve_expiry_to_datetime(ts).tzinfo == timezone.utc

    with pytest.raises(ValueError):
        resolve_expiry_to_datetime("bad-type")

    with pytest.raises(ValueError):
        resolve_expiry_to_datetime("bad-type")

    class FakeDateTime:
        @staticmethod
        def fromtimestamp(ts, tz=None):
            raise ValueError("bad timestamp")

    monkeypatch.setattr("src.common.time_helpers.expiry_conversions.datetime", FakeDateTime)
    with pytest.raises(ValueError):
        resolve_expiry_to_datetime(123, instrument_name="instr")


def test_is_market_expired_threshold():
    fresh = (EPOCH_START + timedelta(days=1)).isoformat()
    assert is_market_expired(fresh) is False

    past = (EPOCH_START - timedelta(days=1)).isoformat()
    assert is_market_expired(past) is True
