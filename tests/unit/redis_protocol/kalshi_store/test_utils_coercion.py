"""Comprehensive unit tests for utils_coercion.py."""

import math
from collections import Counter
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from common.exceptions import DataError, ValidationError
from common.redis_protocol.kalshi_store.utils_coercion import (
    _convert_numeric_field,
    _counter_value,
    _format_probability_value,
    _normalise_hash,
    _normalize_timestamp,
    _select_timestamp_value,
    _sync_top_of_book_fields,
    _to_optional_float,
    bool_or_default,
    coerce_mapping,
    coerce_sequence,
    convert_numeric_field,
    float_or_default,
    int_or_default,
    string_or_default,
)

_VAL_0_0 = 0.0
_VAL_0_5 = 0.5
_VAL_1_0 = 1.0
_VAL_3_14 = 3.14
_VAL_12_5 = 12.5
_VAL_42_0 = 42.0
_VAL_123_45 = 123.45
_VAL_100_0 = 100.0
_INT_5 = 5
_INT_10 = 10
_INT_42 = 42
_INT_100 = 100
_INT_123 = 123


class TestConvertNumericField:
    """Tests for convert_numeric_field and _convert_numeric_field."""

    def test_converts_numeric_string(self):
        """Test conversion of numeric strings."""
        assert convert_numeric_field("12.5") == pytest.approx(_VAL_12_5)
        assert convert_numeric_field("42") == pytest.approx(_VAL_42_0)
        assert convert_numeric_field("3.14159") == pytest.approx(3.14159)

    def test_converts_numeric_values(self):
        """Test conversion of numeric values."""
        assert convert_numeric_field(_INT_42) == pytest.approx(_VAL_42_0)
        assert convert_numeric_field(_VAL_3_14) == pytest.approx(_VAL_3_14)

    def test_handles_none_and_empty_strings(self):
        """Test that None and empty strings return None."""
        assert convert_numeric_field(None) is None
        assert convert_numeric_field("") is None
        assert convert_numeric_field("None") is None

    def test_returns_none_for_invalid_input(self):
        """Test that invalid inputs return None (delegated to coerce_float_optional)."""
        result = convert_numeric_field("not_a_number")
        assert result is None

    def test_returns_none_for_non_convertible(self):
        """Test that non-convertible types return None (delegated to coerce_float_optional)."""
        result = convert_numeric_field(["list", "value"])
        assert result is None

    def test_handles_whitespace_strings(self):
        """Test handling of whitespace-only strings."""
        assert convert_numeric_field("   ") is None
        assert convert_numeric_field("\t") is None
        assert convert_numeric_field("\n") is None


class TestCoerceMapping:
    """Tests for coerce_mapping."""

    def test_returns_dict_unchanged(self):
        """Test that dict is returned unchanged."""
        input_dict = {"key": "value", "num": _INT_42}
        result = coerce_mapping(input_dict)
        assert result == input_dict
        assert result is input_dict

    def test_converts_mapping_like_objects(self):
        """Test conversion of mapping-like objects."""
        mock_mapping = MagicMock()
        mock_mapping.items.return_value = [("a", 1), ("b", 2)]
        result = coerce_mapping(mock_mapping)
        assert result == {"a": 1, "b": 2}

    def test_returns_empty_dict_for_non_mapping(self):
        """Test that non-mapping objects return empty dict."""
        assert coerce_mapping(None) == {}
        assert coerce_mapping("string") == {}
        assert coerce_mapping(_INT_42) == {}
        assert coerce_mapping([1, 2, 3]) == {}

    def test_handles_failed_items_conversion(self):
        """Test handling when items() exists but conversion fails."""
        mock_obj = MagicMock()
        mock_obj.items.side_effect = ValueError("Conversion failed")
        result = coerce_mapping(mock_obj)
        assert result == {}


class TestCoerceSequence:
    """Tests for coerce_sequence."""

    def test_returns_list_unchanged(self):
        """Test that list is returned as list."""
        input_list = [1, 2, 3]
        result = coerce_sequence(input_list)
        assert result == input_list

    def test_converts_tuple_to_list(self):
        """Test tuple conversion to list."""
        result = coerce_sequence((1, 2, 3))
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_converts_set_to_list(self):
        """Test set conversion to list."""
        result = coerce_sequence({1, 2, 3})
        assert sorted(result) == [1, 2, 3]
        assert isinstance(result, list)

    def test_returns_empty_list_for_none(self):
        """Test that None returns empty list."""
        assert coerce_sequence(None) == []

    def test_converts_iterables(self):
        """Test conversion of iterable objects."""
        result = coerce_sequence(range(_INT_5))
        assert result == [0, 1, 2, 3, 4]

    def test_returns_empty_list_for_non_iterable(self):
        """Test that non-iterable returns empty list."""
        assert coerce_sequence(_INT_42) == []

    def test_handles_failed_iteration(self):
        """Test handling when iteration fails."""
        mock_iter = MagicMock()
        mock_iter.__iter__.side_effect = ValueError("Iteration failed")
        result = coerce_sequence(mock_iter)
        assert result == []


class TestStringOrDefault:
    """Tests for string_or_default."""

    def test_returns_string_unchanged(self):
        """Test that string is returned unchanged."""
        assert string_or_default("hello") == "hello"
        assert string_or_default("test") == "test"

    def test_decodes_bytes(self):
        """Test byte decoding."""
        assert string_or_default(b"hello") == "hello"
        assert string_or_default(bytearray(b"world")) == "world"

    def test_trims_whitespace_when_requested(self):
        """Test whitespace trimming."""
        assert string_or_default("  hello  ", trim=True) == "hello"
        assert string_or_default("  hello  ", trim=False) == "  hello  "
        assert string_or_default(b"  world  ", trim=True) == "world"

    def test_returns_default_for_none(self):
        """Test default value for None."""
        assert string_or_default(None) == ""
        assert string_or_default(None, default="fallback") == "fallback"

    def test_converts_non_string_types(self):
        """Test conversion of non-string types."""
        assert string_or_default(_INT_42) == "42"
        assert string_or_default(_VAL_3_14) == "3.14"
        assert string_or_default(True) == "True"

    def test_handles_unicode_in_bytes(self):
        """Test handling of unicode in bytes."""
        assert string_or_default(b"\xc3\xa9") == "é"
        assert string_or_default(b"invalid\xff\xfe", default="fallback") != "fallback"


class TestIntOrDefault:
    """Tests for int_or_default."""

    def test_returns_int_unchanged(self):
        """Test that int is returned unchanged."""
        assert int_or_default(_INT_42) == _INT_42
        assert int_or_default(0) == 0
        assert int_or_default(-_INT_5) == -_INT_5

    def test_converts_float_to_int(self):
        """Test float conversion to int."""
        assert int_or_default(_VAL_42_0) == _INT_42
        assert int_or_default(_VAL_3_14) == 3
        assert int_or_default(99.9) == 99

    def test_converts_string_to_int(self):
        """Test string conversion to int."""
        assert int_or_default("42") == _INT_42
        assert int_or_default("123") == _INT_123
        assert int_or_default("3.14") == 3

    def test_converts_bytes_to_int(self):
        """Test byte conversion to int."""
        assert int_or_default(b"42") == _INT_42
        assert int_or_default(bytearray(b"123")) == _INT_123

    def test_returns_default_for_none(self):
        """Test default value for None."""
        assert int_or_default(None) == 0
        assert int_or_default(None, default=_INT_100) == _INT_100

    def test_returns_default_for_invalid_string(self):
        """Test default value for invalid strings."""
        assert int_or_default("not_a_number") == 0
        assert int_or_default("not_a_number", default=_INT_42) == _INT_42

    def test_converts_bool_to_int(self):
        """Test boolean conversion to int."""
        assert int_or_default(True) == 1
        assert int_or_default(False) == 0


class TestFloatOrDefault:
    """Tests for float_or_default."""

    def test_returns_float_unchanged(self):
        """Test that float is returned unchanged."""
        assert float_or_default(_VAL_3_14) == pytest.approx(_VAL_3_14)
        assert float_or_default(_VAL_0_0) == pytest.approx(_VAL_0_0)

    def test_converts_int_to_float(self):
        """Test int conversion to float."""
        assert float_or_default(_INT_42) == pytest.approx(_VAL_42_0)
        assert float_or_default(0) == pytest.approx(_VAL_0_0)

    def test_converts_string_to_float(self):
        """Test string conversion to float."""
        assert float_or_default("3.14") == pytest.approx(_VAL_3_14)
        assert float_or_default("42") == pytest.approx(_VAL_42_0)

    def test_returns_default_for_none(self):
        """Test default value for None."""
        assert float_or_default(None) == pytest.approx(_VAL_0_0)
        assert float_or_default(None, default=_VAL_100_0) == pytest.approx(_VAL_100_0)

    def test_returns_default_for_invalid_string(self):
        """Test default value for invalid strings."""
        assert float_or_default("not_a_number") == pytest.approx(_VAL_0_0)
        assert float_or_default("invalid", default=_VAL_42_0) == pytest.approx(_VAL_42_0)

    def test_raises_error_when_requested(self):
        """Test error raising mode."""
        with pytest.raises(ValueError, match="Expected numeric value"):
            float_or_default(None, raise_on_error=True)
        with pytest.raises(ValueError):
            float_or_default("not_a_number", raise_on_error=True)

    def test_uses_custom_error_message(self):
        """Test custom error messages."""
        with pytest.raises(ValueError, match="Custom error"):
            float_or_default(None, raise_on_error=True, error_message="Custom error: {value}")


class TestBoolOrDefault:
    """Tests for bool_or_default."""

    def test_returns_bool_unchanged(self):
        """Test that bool is returned unchanged."""
        assert bool_or_default(True, False) is True
        assert bool_or_default(False, True) is False

    def test_converts_0_and_1(self):
        """Test conversion of 0 and 1."""
        assert bool_or_default(0, True) is False
        assert bool_or_default(1, False) is True

    def test_returns_default_for_other_values(self):
        """Test default value for other values."""
        assert bool_or_default(_INT_42, True) is True
        assert bool_or_default(_INT_42, False) is False
        assert bool_or_default("string", True) is True

    def test_parses_string_representations(self):
        """Test string parsing when enabled."""
        assert bool_or_default("true", False, parse_strings=True) is True
        assert bool_or_default("True", False, parse_strings=True) is True
        assert bool_or_default("yes", False, parse_strings=True) is True
        assert bool_or_default("on", False, parse_strings=True) is True
        assert bool_or_default("1", False, parse_strings=True) is True
        assert bool_or_default("false", True, parse_strings=True) is False
        assert bool_or_default("False", True, parse_strings=True) is False
        assert bool_or_default("no", True, parse_strings=True) is False
        assert bool_or_default("off", True, parse_strings=True) is False
        assert bool_or_default("0", True, parse_strings=True) is False

    def test_ignores_strings_when_parsing_disabled(self):
        """Test that strings are ignored when parse_strings is False."""
        assert bool_or_default("true", False, parse_strings=False) is False
        assert bool_or_default("false", True, parse_strings=False) is True

    def test_handles_whitespace_in_strings(self):
        """Test string parsing with whitespace."""
        assert bool_or_default("  true  ", False, parse_strings=True) is True
        assert bool_or_default("  FALSE  ", True, parse_strings=True) is False


class TestCounterValue:
    """Tests for _counter_value."""

    def test_returns_counter_value(self):
        """Test returning counter value for existing key."""
        counter = Counter({"a": 3, "b": 5})
        assert _counter_value(counter, "a") == 3
        assert _counter_value(counter, "b") == 5

    def test_returns_zero_for_missing_key(self):
        """Test returning 0 for missing key."""
        counter = Counter({"a": 3})
        assert _counter_value(counter, "b") == 0
        assert _counter_value(counter, "missing") == 0


class TestToOptionalFloat:
    """Tests for _to_optional_float."""

    def test_converts_numeric_values(self):
        """Test conversion of numeric values."""
        assert _to_optional_float(_VAL_3_14, context="test") == pytest.approx(_VAL_3_14)
        assert _to_optional_float(_INT_42, context="test") == pytest.approx(_VAL_42_0)
        assert _to_optional_float("123.45", context="test") == pytest.approx(_VAL_123_45)

    def test_returns_none_for_empty_values(self):
        """Test returning None for empty values."""
        assert _to_optional_float(None, context="test") is None
        assert _to_optional_float("", context="test") is None
        assert _to_optional_float(b"", context="test") is None

    def test_raises_runtime_error_for_invalid_values(self):
        """Test raising RuntimeError for invalid values."""
        with pytest.raises(RuntimeError, match="Invalid test value"):
            _to_optional_float("not_a_number", context="test")
        with pytest.raises(RuntimeError, match="Invalid price value"):
            _to_optional_float("abc", context="price")


class TestNormaliseHash:
    """Tests for _normalise_hash."""

    def test_delegates_to_canonical_implementation(self):
        """Test that _normalise_hash calls canonical normalise_hash implementation."""
        raw_hash = {b"key": b"value", b"num": b"42"}
        result = _normalise_hash(raw_hash)
        assert isinstance(result, dict)
        assert all(isinstance(k, str) for k in result.keys())


class TestSyncTopOfBookFields:
    """Tests for _sync_top_of_book_fields."""

    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_bid")
    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_ask")
    def test_updates_scalar_fields(self, mock_extract_ask, mock_extract_bid):
        """Test that scalar fields are updated correctly."""
        mock_extract_bid.return_value = (95, _INT_100)
        mock_extract_ask.return_value = (98, 50)

        snapshot = {"yes_bids": [], "yes_asks": []}
        _sync_top_of_book_fields(snapshot)

        assert snapshot["yes_bid"] == "95"
        assert snapshot["yes_bid_size"] == "100"
        assert snapshot["yes_ask"] == "98"
        assert snapshot["yes_ask_size"] == "50"

    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_bid")
    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_ask")
    def test_handles_none_values(self, mock_extract_ask, mock_extract_bid):
        """Test handling of None values."""
        mock_extract_bid.return_value = (None, None)
        mock_extract_ask.return_value = (None, None)

        snapshot = {}
        _sync_top_of_book_fields(snapshot)

        assert snapshot["yes_bid"] == ""
        assert snapshot["yes_bid_size"] == ""
        assert snapshot["yes_ask"] == ""
        assert snapshot["yes_ask_size"] == ""

    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_bid")
    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_ask")
    def test_handles_missing_orderbook_data(self, mock_extract_ask, mock_extract_bid):
        """Test handling when orderbook data is missing."""
        mock_extract_bid.return_value = (50, _INT_10)
        mock_extract_ask.return_value = (55, 20)

        snapshot = {}
        _sync_top_of_book_fields(snapshot)

        mock_extract_bid.assert_called_once_with(None)
        mock_extract_ask.assert_called_once_with(None)

    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_bid")
    @patch("common.redis_protocol.kalshi_store.utils_coercion.extract_best_ask")
    def test_handles_mixed_none_values(self, mock_extract_ask, mock_extract_bid):
        """Test handling of mixed None and numeric values."""
        mock_extract_bid.return_value = (95, None)
        mock_extract_ask.return_value = (None, 50)

        snapshot = {"yes_bids": [], "yes_asks": []}
        _sync_top_of_book_fields(snapshot)

        assert snapshot["yes_bid"] == "95"
        assert snapshot["yes_bid_size"] == ""
        assert snapshot["yes_ask"] == ""
        assert snapshot["yes_ask_size"] == "50"


class TestFormatProbabilityValue:
    """Tests for _format_probability_value."""

    def test_formats_probability_values(self):
        """Test formatting of probability values."""
        assert _format_probability_value(_VAL_0_5) == "0.5"
        assert _format_probability_value(_VAL_1_0) == "1"
        assert _format_probability_value(_VAL_0_0) == "0"

    def test_removes_trailing_zeros(self):
        """Test removal of trailing zeros."""
        assert _format_probability_value(0.12300000) == "0.123"
        assert _format_probability_value(0.10000000) == "0.1"

    def test_limits_decimal_places(self):
        """Test decimal precision."""
        result = _format_probability_value(0.123456789012345)
        parts = result.split(".")
        assert len(parts) == 2
        assert len(parts[1]) <= _INT_10

    def test_raises_type_error_for_non_numeric(self):
        """Test raising TypeError for non-numeric values."""
        with pytest.raises(TypeError, match="Probability value must be float-compatible"):
            _format_probability_value("not_a_number")
        with pytest.raises(TypeError):
            _format_probability_value(None)

    def test_raises_type_error_for_infinite_values(self):
        """Test raising TypeError for infinite values."""
        with pytest.raises(TypeError, match="Probability value must be finite"):
            _format_probability_value(math.inf)
        with pytest.raises(TypeError, match="Probability value must be finite"):
            _format_probability_value(-math.inf)
        with pytest.raises(TypeError, match="Probability value must be finite"):
            _format_probability_value(math.nan)

    def test_handles_integer_input(self):
        """Test handling of integer input."""
        assert _format_probability_value(0) == "0"
        assert _format_probability_value(1) == "1"

    def test_handles_very_small_values(self):
        """Test handling of very small values."""
        result = _format_probability_value(0.0000000001)
        assert result == "0.0000000001"


class TestNormalizeTimestamp:
    """Tests for _normalize_timestamp."""

    @patch("common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization.normalize_timestamp")
    def test_delegates_to_canonical_implementation(self, mock_normalize):
        """Test delegation to canonical normalize_timestamp."""
        timestamp = 1700000000
        expected_result = "2023-11-14T22:13:20+00:00"
        mock_normalize.return_value = expected_result

        result = _normalize_timestamp(timestamp)

        assert result == expected_result
        mock_normalize.assert_called_once_with(timestamp)

    @patch("common.redis_protocol.kalshi_store.metadata_helpers.timestamp_normalization.normalize_timestamp")
    def test_handles_none_value(self, mock_normalize):
        """Test handling of None value."""
        mock_normalize.return_value = None

        result = _normalize_timestamp(None)

        assert result is None


class TestSelectTimestampValue:
    """Tests for _select_timestamp_value."""

    @patch("common.redis_protocol.kalshi_store.metadata.KalshiMetadataAdapter")
    def test_delegates_to_metadata_adapter(self, mock_adapter_class):
        """Test delegation to KalshiMetadataAdapter."""
        market_data = {"timestamp1": None, "timestamp2": 1700000000}
        fields = ["timestamp1", "timestamp2"]
        expected_result = 1700000000
        mock_adapter_class.select_timestamp_value.return_value = expected_result

        result = _select_timestamp_value(market_data, fields)

        assert result == expected_result
        mock_adapter_class.select_timestamp_value.assert_called_once_with(market_data, fields)


class TestDefaultWeatherStationLoader:
    """Tests for _default_weather_station_loader."""

    @patch("common.redis_protocol.kalshi_store.utils_coercion.load_weather_station_mapping")
    def test_loads_weather_station_mapping(self, mock_load):
        """Test successful loading of weather station mapping."""
        from common.redis_protocol.kalshi_store.utils_coercion import (
            _default_weather_station_loader,
        )

        expected_mapping = {"KJFK": {"name": "JFK Airport"}}
        mock_load.return_value = expected_mapping

        result = _default_weather_station_loader()

        assert result == expected_mapping
        mock_load.assert_called_once()

    @patch("common.redis_protocol.kalshi_store.utils_coercion.load_weather_station_mapping")
    def test_raises_weather_config_error(self, mock_load):
        """Test handling of WeatherConfigError."""
        from common.config.weather import WeatherConfigError
        from common.redis_protocol.kalshi_store.utils_coercion import (
            _default_weather_station_loader,
        )

        mock_load.side_effect = WeatherConfigError("Config error")

        with pytest.raises(WeatherConfigError):
            _default_weather_station_loader()

    @patch("common.redis_protocol.kalshi_store.utils_coercion.load_weather_station_mapping")
    def test_wraps_unexpected_errors(self, mock_load):
        """Test wrapping of unexpected errors."""
        from common.config.weather import WeatherConfigError
        from common.redis_protocol.kalshi_store.utils_coercion import (
            _default_weather_station_loader,
        )

        mock_load.side_effect = OSError("File not found")

        with pytest.raises(WeatherConfigError, match="Weather station mapping loading failed unexpectedly"):
            _default_weather_station_loader()
