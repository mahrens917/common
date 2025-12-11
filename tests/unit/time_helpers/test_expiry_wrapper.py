"""Tests for DateTimeExpiry wrapper class."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from common.exceptions import ValidationError
from common.time_helpers.expiry_wrapper import DateTimeExpiry


class TestDateTimeExpiryInit:
    """Tests for DateTimeExpiry initialization."""

    def test_init_from_datetime(self) -> None:
        """Initializes from datetime."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert expiry.datetime_value == dt

    def test_init_from_datetime_expiry(self) -> None:
        """Initializes from another DateTimeExpiry."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        original = DateTimeExpiry(dt)
        copy = DateTimeExpiry(original)

        assert copy.datetime_value == original.datetime_value

    def test_init_from_iso_string(self) -> None:
        """Initializes from ISO string."""
        iso_str = "2025-01-10T00:00:00Z"
        expiry = DateTimeExpiry(iso_str)

        assert expiry.datetime_value.year == 2025
        assert expiry.datetime_value.month == 1
        assert expiry.datetime_value.day == 10

    def test_init_from_float_time_point(self) -> None:
        """Initializes from float time point."""
        time_point = 0.5  # Small time point value
        expiry = DateTimeExpiry(time_point)

        assert isinstance(expiry.datetime_value, datetime)

    def test_init_from_int_time_point(self) -> None:
        """Initializes from int time point."""
        time_point = 1  # Small time point value
        expiry = DateTimeExpiry(time_point)

        assert isinstance(expiry.datetime_value, datetime)


class TestDateTimeExpiryProperties:
    """Tests for DateTimeExpiry properties."""

    def test_time_point_property(self) -> None:
        """Returns time point."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert isinstance(expiry.time_point, float)
        assert expiry.time_point > 0

    def test_iso_string_property(self) -> None:
        """Returns ISO string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert expiry.iso_string.startswith("2025-01-10")


class TestDateTimeExpiryComparisons:
    """Tests for DateTimeExpiry comparison operators."""

    def test_eq_with_datetime_expiry(self) -> None:
        """Equals another DateTimeExpiry with same value."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry1 = DateTimeExpiry(dt)
        expiry2 = DateTimeExpiry(dt)

        assert expiry1 == expiry2

    def test_eq_with_datetime(self) -> None:
        """Equals a datetime with same value."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert expiry == dt

    def test_eq_with_iso_string(self) -> None:
        """Equals an ISO string with same value."""
        iso_str = "2025-01-10T00:00:00+00:00"
        expiry = DateTimeExpiry(iso_str)

        assert expiry == iso_str

    def test_eq_with_invalid_string_returns_false(self) -> None:
        """Returns False when comparing with invalid string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert not (expiry == "invalid_string")

    def test_eq_with_time_point(self) -> None:
        """Equals a time point with same value."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)
        time_point = expiry.time_point

        assert expiry == time_point

    def test_eq_with_unsupported_type_returns_not_implemented(self) -> None:
        """Returns NotImplemented for unsupported types."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        result = expiry.__eq__([1, 2, 3])
        assert result is NotImplemented

    def test_lt_with_datetime(self) -> None:
        """Less than comparison with datetime."""
        dt1 = datetime(2025, 1, 10, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 11, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt1)

        assert expiry < dt2
        assert not (expiry < dt1)

    def test_lt_with_invalid_string_returns_false(self) -> None:
        """Returns False when comparing with invalid string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert not (expiry < "invalid_string")

    def test_lt_with_unsupported_type_returns_not_implemented(self) -> None:
        """Returns NotImplemented for unsupported types."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        result = expiry.__lt__([1, 2, 3])
        assert result is NotImplemented

    def test_le_with_datetime(self) -> None:
        """Less than or equal comparison with datetime."""
        dt1 = datetime(2025, 1, 10, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 11, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt1)

        assert expiry <= dt2
        assert expiry <= dt1

    def test_gt_with_datetime(self) -> None:
        """Greater than comparison with datetime."""
        dt1 = datetime(2025, 1, 11, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt1)

        assert expiry > dt2
        assert not (expiry > dt1)

    def test_gt_with_invalid_string_returns_false(self) -> None:
        """Returns False when comparing with invalid string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert not (expiry > "invalid_string")

    def test_gt_with_unsupported_type_returns_not_implemented(self) -> None:
        """Returns NotImplemented for unsupported types."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        result = expiry.__gt__([1, 2, 3])
        assert result is NotImplemented

    def test_ge_with_datetime(self) -> None:
        """Greater than or equal comparison with datetime."""
        dt1 = datetime(2025, 1, 11, tzinfo=timezone.utc)
        dt2 = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt1)

        assert expiry >= dt2
        assert expiry >= dt1


class TestDateTimeExpiryStringMethods:
    """Tests for DateTimeExpiry string methods."""

    def test_str_returns_iso_string(self) -> None:
        """Returns ISO string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        assert str(expiry).startswith("2025-01-10")


class TestDateTimeExpiryHash:
    """Tests for DateTimeExpiry hashing."""

    def test_hash_is_consistent(self) -> None:
        """Hash is consistent for same value."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry1 = DateTimeExpiry(dt)
        expiry2 = DateTimeExpiry(dt)

        assert hash(expiry1) == hash(expiry2)

    def test_can_be_used_in_set(self) -> None:
        """Can be used in a set."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry1 = DateTimeExpiry(dt)
        expiry2 = DateTimeExpiry(dt)

        expiry_set = {expiry1, expiry2}
        assert len(expiry_set) == 1

    def test_can_be_used_as_dict_key(self) -> None:
        """Can be used as dict key."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        expiry_dict = {expiry: "value"}
        assert expiry_dict[expiry] == "value"


class TestDateTimeExpiryToDatetime:
    """Tests for _to_datetime conversion method."""

    def test_to_datetime_with_string_z_suffix(self) -> None:
        """Converts string with Z suffix."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        result = expiry._to_datetime("2025-01-10T00:00:00Z")
        assert isinstance(result, datetime)

    def test_to_datetime_with_invalid_string(self) -> None:
        """Returns None for invalid string."""
        dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
        expiry = DateTimeExpiry(dt)

        result = expiry._to_datetime("not-a-date")
        assert result is None
