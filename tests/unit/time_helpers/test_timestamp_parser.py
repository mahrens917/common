"""Tests for time_helpers.timestamp_parser covering uncovered branches."""

import math
from datetime import datetime, timezone

import pytest

from common.time_helpers.timestamp_parser import (
    MICROSECOND_TIMESTAMP_THRESHOLD,
    MILLISECOND_TIMESTAMP_THRESHOLD,
    NANOSECOND_TIMESTAMP_THRESHOLD,
    parse_timestamp,
)


def test_none_without_allow_none_raises():
    with pytest.raises(ValueError, match="required"):
        parse_timestamp(None)


def test_naive_datetime_gets_utc():
    naive = datetime(2024, 1, 1, 12, 0, 0)
    result = parse_timestamp(naive)
    assert result.tzinfo == timezone.utc
    assert result.year == 2024


def test_aware_datetime_returned_as_utc():
    dt = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    result = parse_timestamp(dt)
    assert result == dt


def test_non_finite_numeric_allow_none():
    assert parse_timestamp(float("inf"), allow_none=True) is None
    assert parse_timestamp(float("nan"), allow_none=True) is None


def test_non_finite_numeric_raises():
    with pytest.raises(ValueError, match="Non-finite"):
        parse_timestamp(float("inf"))


def test_microsecond_timestamp():
    us_ts = MICROSECOND_TIMESTAMP_THRESHOLD + 1_000_000
    result = parse_timestamp(us_ts)
    assert result.tzinfo == timezone.utc


def test_nanosecond_timestamp():
    ns_ts = NANOSECOND_TIMESTAMP_THRESHOLD + 1_000_000_000
    result = parse_timestamp(ns_ts)
    assert result.tzinfo == timezone.utc


def test_millisecond_timestamp():
    ms_ts = MILLISECOND_TIMESTAMP_THRESHOLD + 1000
    result = parse_timestamp(ms_ts)
    assert result.tzinfo == timezone.utc


def test_empty_string_allow_none():
    assert parse_timestamp("", allow_none=True) is None
    assert parse_timestamp("   ", allow_none=True) is None


def test_empty_string_raises():
    with pytest.raises(ValueError, match="empty"):
        parse_timestamp("")


def test_numeric_string():
    ts = str(int(MILLISECOND_TIMESTAMP_THRESHOLD + 5000))
    result = parse_timestamp(ts)
    assert result.tzinfo == timezone.utc


def test_invalid_iso_string_allow_none():
    assert parse_timestamp("not-a-date", allow_none=True) is None


def test_invalid_iso_string_raises():
    with pytest.raises(ValueError):
        parse_timestamp("not-a-date")


def test_iso_string_with_z_suffix():
    result = parse_timestamp("2024-03-01T12:00:00Z")
    assert result.tzinfo == timezone.utc
    assert result.year == 2024
