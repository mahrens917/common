"""Tests for quote timestamp validator module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from common.market_filters.deribit_helpers.quote_timestamp_validator import (
    QuoteTimestampValidator,
)


class TestQuoteTimestampValidatorExtractTimestamp:
    """Tests for QuoteTimestampValidator.extract_timestamp."""

    def test_extract_timestamp_prefers_quote_timestamp(self) -> None:
        """Prefers quote_timestamp attribute."""
        instrument = MagicMock()
        expected_ts = datetime(2024, 12, 1, 12, 0, 0)
        instrument.quote_timestamp = expected_ts
        instrument.mark_price_timestamp = datetime(2024, 12, 1, 11, 0, 0)
        instrument.timestamp = datetime(2024, 12, 1, 10, 0, 0)

        result = QuoteTimestampValidator.extract_timestamp(instrument)

        assert result == expected_ts

    def test_extract_timestamp_uses_mark_price_timestamp_if_no_quote(self) -> None:
        """Uses mark_price_timestamp if quote_timestamp is None."""
        instrument = MagicMock()
        expected_ts = datetime(2024, 12, 1, 11, 0, 0)
        instrument.quote_timestamp = None
        instrument.mark_price_timestamp = expected_ts
        instrument.timestamp = datetime(2024, 12, 1, 10, 0, 0)

        result = QuoteTimestampValidator.extract_timestamp(instrument)

        assert result == expected_ts

    def test_extract_timestamp_uses_timestamp_as_last_resort(self) -> None:
        """Uses timestamp if both quote_timestamp and mark_price_timestamp are None."""
        instrument = MagicMock()
        expected_ts = datetime(2024, 12, 1, 10, 0, 0)
        instrument.quote_timestamp = None
        instrument.mark_price_timestamp = None
        instrument.timestamp = expected_ts

        result = QuoteTimestampValidator.extract_timestamp(instrument)

        assert result == expected_ts

    def test_extract_timestamp_returns_none_when_no_attrs(self) -> None:
        """Returns None when no timestamp attributes exist."""
        instrument = MagicMock(spec=[])

        result = QuoteTimestampValidator.extract_timestamp(instrument)

        assert result is None


class TestQuoteTimestampValidatorValidateTimestamp:
    """Tests for QuoteTimestampValidator.validate_timestamp."""

    def test_validate_timestamp_returns_none_for_valid(self) -> None:
        """Returns None for valid, recent timestamp."""
        quote_ts = datetime(2024, 12, 1, 11, 59, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        max_age = timedelta(minutes=5)

        result = QuoteTimestampValidator.validate_timestamp(quote_ts, current_time, max_age)

        assert result is None

    def test_validate_timestamp_returns_none_for_non_datetime(self) -> None:
        """Returns None for non-datetime quote_timestamp."""
        result = QuoteTimestampValidator.validate_timestamp(
            "not a datetime",
            datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc),
            timedelta(minutes=5),
        )

        assert result is None

    def test_validate_timestamp_returns_future_for_future_quote(self) -> None:
        """Returns 'future_quote' for timestamp in the future."""
        quote_ts = datetime(2024, 12, 1, 12, 10, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        max_age = timedelta(minutes=5)

        result = QuoteTimestampValidator.validate_timestamp(quote_ts, current_time, max_age)

        assert result == "future_quote"

    def test_validate_timestamp_allows_slight_future(self) -> None:
        """Allows timestamps up to 5 seconds in the future."""
        quote_ts = datetime(2024, 12, 1, 12, 0, 4, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        max_age = timedelta(minutes=5)

        result = QuoteTimestampValidator.validate_timestamp(quote_ts, current_time, max_age)

        assert result is None

    def test_validate_timestamp_returns_stale_for_old_quote(self) -> None:
        """Returns 'stale_quote' for timestamp older than max_age."""
        quote_ts = datetime(2024, 12, 1, 11, 50, 0, tzinfo=timezone.utc)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        max_age = timedelta(minutes=5)

        result = QuoteTimestampValidator.validate_timestamp(quote_ts, current_time, max_age)

        assert result == "stale_quote"

    def test_validate_timestamp_normalizes_naive_timestamp(self) -> None:
        """Normalizes naive timestamp to UTC."""
        quote_ts = datetime(2024, 12, 1, 11, 58, 0)
        current_time = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)
        max_age = timedelta(minutes=5)

        result = QuoteTimestampValidator.validate_timestamp(quote_ts, current_time, max_age)

        assert result is None
