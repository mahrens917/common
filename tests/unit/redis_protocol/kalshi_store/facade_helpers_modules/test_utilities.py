"""Tests for facade_helpers_modules utilities."""

from common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization import normalize_timestamp
from common.redis_protocol.kalshi_store.utils_coercion import (
    coerce_mapping,
    float_or_default,
    format_probability_value,
    int_or_default,
    normalise_hash,
    string_or_default,
    sync_top_of_book_fields,
)
from common.redis_protocol.kalshi_store.utils_market import normalise_trade_timestamp


class TestNormaliseHash:
    """Tests for normalise_hash."""

    def test_normalises_bytes_keys(self) -> None:
        """Test normalising bytes keys to strings."""
        raw = {b"key": "value", b"other": 123}
        result = normalise_hash(raw)
        assert "key" in result
        assert result["key"] == "value"

    def test_handles_string_keys(self) -> None:
        """Test handling already-string keys."""
        raw = {"key": "value"}
        result = normalise_hash(raw)
        assert result["key"] == "value"


class TestSyncTopOfBookFields:
    """Tests for sync_top_of_book_fields."""

    def test_syncs_fields(self) -> None:
        """Test syncing top of book fields."""
        snapshot = {"orderbook": '{"yes_bids": {"50": 10}, "yes_asks": {"55": 5}}'}
        sync_top_of_book_fields(snapshot)
        # Function modifies in place


class TestFormatProbabilityValue:
    """Tests for format_probability_value."""

    def test_formats_float(self) -> None:
        """Test formatting float value."""
        result = format_probability_value(0.5)
        assert isinstance(result, str)

    def test_formats_string(self) -> None:
        """Test formatting string value."""
        result = format_probability_value("0.5")
        assert isinstance(result, str)


class TestNormalizeTimestamp:
    """Tests for normalize_timestamp."""

    def test_normalises_iso_timestamp(self) -> None:
        """Test normalising ISO timestamp."""
        result = normalize_timestamp("2024-01-15T10:00:00Z")
        assert result is not None

    def test_returns_none_for_invalid(self) -> None:
        """Test returning None for invalid input."""
        result = normalize_timestamp(None)
        assert result is None


class TestNormaliseTradeTimestamp:
    """Tests for normalise_trade_timestamp."""

    def test_normalises_trade_timestamp(self) -> None:
        """Test normalising trade timestamp."""
        result = normalise_trade_timestamp("2024-01-15T10:00:00Z")
        assert isinstance(result, str)


class TestCoerceMapping:
    """Tests for coerce_mapping."""

    def test_returns_dict_unchanged(self) -> None:
        """Test returning dict unchanged."""
        result = coerce_mapping({"key": "value"})
        assert result == {"key": "value"}

    def test_returns_empty_for_non_dict(self) -> None:
        """Test returning empty dict for non-dict input."""
        result = coerce_mapping("not a dict")
        assert result == {}


class TestStringOrDefault:
    """Tests for string_or_default."""

    def test_returns_string_value(self) -> None:
        """Test returning string value."""
        result = string_or_default("value", "")
        assert result == "value"

    def test_returns_fill_for_none(self) -> None:
        """Test returning fill value for None."""
        result = string_or_default(None, "fill")
        assert result == "fill"


class TestIntOrDefault:
    """Tests for int_or_default."""

    def test_returns_int_value(self) -> None:
        """Test returning int value."""
        result = int_or_default(42, 0)
        assert result == 42

    def test_returns_fill_for_none(self) -> None:
        """Test returning fill value for None."""
        result = int_or_default(None, 0)
        assert result == 0


class TestFloatOrDefault:
    """Tests for float_or_default."""

    def test_returns_float_value(self) -> None:
        """Test returning float value."""
        result = float_or_default(3.14, 0.0)
        assert result == 3.14

    def test_returns_fill_for_none(self) -> None:
        """Test returning fill value for None."""
        result = float_or_default(None, 0.0)
        assert result == 0.0
