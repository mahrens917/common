"""Tests for expiry checker module."""

from datetime import datetime, timezone

from common.market_filters.deribit_helpers.expiry_checker import ExpiryChecker


class TestExpiryCheckerNormalizeExpiry:
    """Tests for ExpiryChecker.normalize_expiry."""

    def test_normalize_expiry_returns_none_for_none(self) -> None:
        """Returns None when value is None."""
        result = ExpiryChecker.normalize_expiry(None)

        assert result is None

    def test_normalize_expiry_adds_utc_to_naive_datetime(self) -> None:
        """Adds UTC timezone to naive datetime."""
        naive_dt = datetime(2024, 12, 1, 12, 0, 0)

        result = ExpiryChecker.normalize_expiry(naive_dt)

        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 12

    def test_normalize_expiry_converts_timezone_aware_to_utc(self) -> None:
        """Converts timezone-aware datetime to UTC."""
        from datetime import timedelta

        pst = timezone(timedelta(hours=-8))
        aware_dt = datetime(2024, 12, 1, 4, 0, 0, tzinfo=pst)

        result = ExpiryChecker.normalize_expiry(aware_dt)

        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_normalize_expiry_returns_none_for_non_datetime(self) -> None:
        """Returns None for non-datetime values."""
        result = ExpiryChecker.normalize_expiry("2024-12-01")

        assert result is None

    def test_normalize_expiry_returns_none_for_int(self) -> None:
        """Returns None for integer values."""
        result = ExpiryChecker.normalize_expiry(1704067200)

        assert result is None


class TestExpiryCheckerIsExpired:
    """Tests for ExpiryChecker.is_expired."""

    def test_is_expired_returns_false_for_none_expiry(self) -> None:
        """Returns False when expiry is None."""
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = ExpiryChecker.is_expired(None, current_time)

        assert result is False

    def test_is_expired_returns_true_when_expired(self) -> None:
        """Returns True when expiry is before current time."""
        expiry = datetime(2024, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = ExpiryChecker.is_expired(expiry, current_time)

        assert result is True

    def test_is_expired_returns_true_when_exactly_equal(self) -> None:
        """Returns True when expiry equals current time."""
        expiry = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = ExpiryChecker.is_expired(expiry, current_time)

        assert result is True

    def test_is_expired_returns_false_when_not_expired(self) -> None:
        """Returns False when expiry is after current time."""
        expiry = datetime(2024, 12, 1, 14, 0, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)

        result = ExpiryChecker.is_expired(expiry, current_time)

        assert result is False
