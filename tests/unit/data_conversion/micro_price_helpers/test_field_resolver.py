"""Tests for field resolver module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.data_conversion.micro_price_helpers.field_resolver import FieldResolver
from common.exceptions import ValidationError


class TestFieldResolverResolveSymbolForLogging:
    """Tests for FieldResolver.resolve_symbol_for_logging."""

    def test_returns_symbol_when_present(self) -> None:
        """Returns symbol attribute when present."""
        instrument = MagicMock()
        instrument.symbol = "BTC-25JAN25-50000-C"

        result = FieldResolver.resolve_symbol_for_logging(instrument)

        assert result == "BTC-25JAN25-50000-C"

    def test_returns_instrument_name_when_no_symbol(self) -> None:
        """Returns instrument_name when symbol is not present."""
        instrument = MagicMock()
        instrument.symbol = None
        instrument.instrument_name = "BTC-OPTIONS-50000"

        result = FieldResolver.resolve_symbol_for_logging(instrument)

        assert result == "BTC-OPTIONS-50000"

    def test_returns_unknown_when_both_missing(self) -> None:
        """Returns 'unknown' when both symbol and instrument_name are missing."""
        instrument = MagicMock()
        instrument.symbol = None
        instrument.instrument_name = None

        result = FieldResolver.resolve_symbol_for_logging(instrument)

        assert result == "unknown"

    def test_prefers_symbol_over_instrument_name(self) -> None:
        """Prefers symbol over instrument_name."""
        instrument = MagicMock()
        instrument.symbol = "SYM123"
        instrument.instrument_name = "INST456"

        result = FieldResolver.resolve_symbol_for_logging(instrument)

        assert result == "SYM123"


class TestFieldResolverResolveInstrumentName:
    """Tests for FieldResolver.resolve_instrument_name."""

    def test_returns_instrument_name_when_present(self) -> None:
        """Returns instrument_name when present."""
        instrument = MagicMock()
        instrument.instrument_name = "BTC-OPTIONS-50000"

        result = FieldResolver.resolve_instrument_name(instrument)

        assert result == "BTC-OPTIONS-50000"

    def test_returns_symbol_when_no_instrument_name(self) -> None:
        """Returns symbol when instrument_name is not present."""
        instrument = MagicMock()
        instrument.instrument_name = None
        instrument.symbol = "BTC-25JAN25-50000-C"

        result = FieldResolver.resolve_instrument_name(instrument)

        assert result == "BTC-25JAN25-50000-C"

    def test_raises_validation_error_when_both_missing(self) -> None:
        """Raises ValidationError when both are missing."""
        instrument = MagicMock()
        instrument.instrument_name = None
        instrument.symbol = None

        with pytest.raises(ValidationError) as exc_info:
            FieldResolver.resolve_instrument_name(instrument)

        assert "lacks both instrument_name and symbol" in str(exc_info.value)

    def test_prefers_instrument_name_over_symbol(self) -> None:
        """Prefers instrument_name over symbol."""
        instrument = MagicMock()
        instrument.instrument_name = "INST456"
        instrument.symbol = "SYM123"

        result = FieldResolver.resolve_instrument_name(instrument)

        assert result == "INST456"


class TestFieldResolverResolveExpiryDatetime:
    """Tests for FieldResolver.resolve_expiry_datetime."""

    def test_converts_int_timestamp_to_datetime(self) -> None:
        """Converts integer timestamp to datetime."""
        timestamp = 1705320000

        result = FieldResolver.resolve_expiry_datetime(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_returns_datetime_as_is(self) -> None:
        """Returns datetime object unchanged."""
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = FieldResolver.resolve_expiry_datetime(dt)

        assert result == dt

    def test_raises_type_error_for_invalid_type(self) -> None:
        """Raises TypeError for invalid types."""
        with pytest.raises(TypeError) as exc_info:
            FieldResolver.resolve_expiry_datetime("2025-01-15")

        assert "Invalid expiry type" in str(exc_info.value)


class TestFieldResolverResolveQuoteTimestamp:
    """Tests for FieldResolver.resolve_quote_timestamp."""

    def test_uses_quote_timestamp_when_present(self) -> None:
        """Uses quote_timestamp when present."""
        instrument = MagicMock()
        instrument.quote_timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        instrument.mark_price_timestamp = None
        instrument.timestamp = None

        result = FieldResolver.resolve_quote_timestamp(instrument)

        assert result == instrument.quote_timestamp

    def test_uses_mark_price_timestamp_as_fallback(self) -> None:
        """Uses mark_price_timestamp when quote_timestamp is not present."""
        instrument = MagicMock()
        instrument.quote_timestamp = None
        instrument.mark_price_timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        instrument.timestamp = None

        result = FieldResolver.resolve_quote_timestamp(instrument)

        assert result == instrument.mark_price_timestamp

    def test_uses_timestamp_as_fallback(self) -> None:
        """Uses timestamp when quote_timestamp and mark_price_timestamp are not present."""
        instrument = MagicMock()
        instrument.quote_timestamp = None
        instrument.mark_price_timestamp = None
        instrument.timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = FieldResolver.resolve_quote_timestamp(instrument)

        assert result == instrument.timestamp

    def test_adds_utc_when_tzinfo_is_none(self) -> None:
        """Adds UTC timezone when datetime has no timezone."""
        instrument = MagicMock()
        instrument.quote_timestamp = datetime(2025, 1, 15, 12, 0, 0)
        instrument.mark_price_timestamp = None
        instrument.timestamp = None

        result = FieldResolver.resolve_quote_timestamp(instrument)

        assert result.tzinfo == timezone.utc

    def test_returns_current_time_when_all_missing(self) -> None:
        """Returns current time when all timestamps are missing."""
        instrument = MagicMock()
        instrument.quote_timestamp = None
        instrument.mark_price_timestamp = None
        instrument.timestamp = None

        with patch("common.time_utils.get_current_utc") as mock_get_time:
            mock_get_time.return_value = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

            result = FieldResolver.resolve_quote_timestamp(instrument)

            assert result == datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
