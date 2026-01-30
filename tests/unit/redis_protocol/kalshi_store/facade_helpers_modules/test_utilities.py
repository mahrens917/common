"""Tests for facade_helpers_modules utilities."""

import pytest

from common.redis_protocol.kalshi_store.facade_helpers_modules.utilities import StaticUtilities


class TestNormaliseHash:
    """Tests for normalise_hash."""

    def test_normalises_bytes_keys(self) -> None:
        """Test normalising bytes keys to strings."""
        raw = {b"key": "value", b"other": 123}
        result = StaticUtilities.normalise_hash(raw)
        assert "key" in result
        assert result["key"] == "value"

    def test_handles_string_keys(self) -> None:
        """Test handling already-string keys."""
        raw = {"key": "value"}
        result = StaticUtilities.normalise_hash(raw)
        assert result["key"] == "value"


class TestSyncTopOfBookFields:
    """Tests for sync_top_of_book_fields."""

    def test_syncs_fields(self) -> None:
        """Test syncing top of book fields."""
        snapshot = {"orderbook": '{"yes_bids": {"50": 10}, "yes_asks": {"55": 5}}'}
        StaticUtilities.sync_top_of_book_fields(snapshot)
        # Function modifies in place


class TestFormatProbabilityValue:
    """Tests for format_probability_value."""

    def test_formats_float(self) -> None:
        """Test formatting float value."""
        result = StaticUtilities.format_probability_value(0.5)
        assert isinstance(result, str)

    def test_formats_string(self) -> None:
        """Test formatting string value."""
        result = StaticUtilities.format_probability_value("0.5")
        assert isinstance(result, str)


class TestNormalizeTimestamp:
    """Tests for normalize_timestamp."""

    def test_normalises_iso_timestamp(self) -> None:
        """Test normalising ISO timestamp."""
        result = StaticUtilities.normalize_timestamp("2024-01-15T10:00:00Z")
        assert result is not None

    def test_returns_none_for_invalid(self) -> None:
        """Test returning None for invalid input."""
        result = StaticUtilities.normalize_timestamp(None)
        assert result is None


class TestNormaliseTradeTimestamp:
    """Tests for normalise_trade_timestamp."""

    def test_normalises_trade_timestamp(self) -> None:
        """Test normalising trade timestamp."""
        result = StaticUtilities.normalise_trade_timestamp("2024-01-15T10:00:00Z")
        assert isinstance(result, str)


class TestCoerceMapping:
    """Tests for coerce_mapping."""

    def test_returns_dict_unchanged(self) -> None:
        """Test returning dict unchanged."""
        result = StaticUtilities.coerce_mapping({"key": "value"})
        assert result == {"key": "value"}

    def test_returns_empty_for_non_dict(self) -> None:
        """Test returning empty dict for non-dict input."""
        result = StaticUtilities.coerce_mapping("not a dict")
        assert result == {}


class TestStringOrDefault:
    """Tests for string_or_default."""

    def test_returns_string_value(self) -> None:
        """Test returning string value."""
        result = StaticUtilities.string_or_default("value", "")
        assert result == "value"

    def test_returns_fallback_for_none(self) -> None:
        """Test returning fallback for None."""
        result = StaticUtilities.string_or_default(None, "fallback")
        assert result == "fallback"


class TestIntOrDefault:
    """Tests for int_or_default."""

    def test_returns_int_value(self) -> None:
        """Test returning int value."""
        result = StaticUtilities.int_or_default(42, 0)
        assert result == 42

    def test_returns_fallback_for_none(self) -> None:
        """Test returning fallback for None."""
        result = StaticUtilities.int_or_default(None, 0)
        assert result == 0


class TestFloatOrDefault:
    """Tests for float_or_default."""

    def test_returns_float_value(self) -> None:
        """Test returning float value."""
        result = StaticUtilities.float_or_default(3.14, 0.0)
        assert result == 3.14

    def test_returns_fallback_for_none(self) -> None:
        """Test returning fallback for None."""
        result = StaticUtilities.float_or_default(None, 0.0)
        assert result == 0.0
