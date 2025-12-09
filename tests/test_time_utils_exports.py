import datetime

import pytest

from src.common import time_utils


def test_current_utc_is_timezone_aware():
    now = time_utils.get_current_utc()
    assert isinstance(now, datetime.datetime)
    assert now.tzinfo is not None
    assert time_utils.ensure_timezone_aware(now).tzinfo is not None


def test_parse_and_format_timestamp_round_trip():
    timestamp = datetime.datetime.fromtimestamp(1_600_000_000, tz=datetime.timezone.utc)
    parsed = time_utils.parse_timestamp(int(timestamp.timestamp()))
    assert isinstance(parsed, datetime.datetime)
    assert time_utils.get_time_from_epoch(parsed) == time_utils.get_time_from_epoch(parsed)
    formatted = time_utils.format_datetime(parsed)
    assert str(timestamp.year) in formatted


def test_expiry_validation_helpers():
    expiry = time_utils.get_datetime_from_time_point(0.0).isoformat()
    time_utils.validate_expiry_hour(time_utils.DERIBIT_EXPIRY_HOUR)
    assert isinstance(time_utils.is_market_expired(expiry), bool)


@pytest.mark.parametrize("hour", [0, 12, 23])
def test_fixed_time_point(hour: int):
    iso_string = f"2020-09-13T{hour:02d}:00:00+00:00"
    time_point = time_utils.get_fixed_time_point(iso_string)
    assert time_point is not None
