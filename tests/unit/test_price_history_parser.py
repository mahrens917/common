import pytest

from common.price_history_parser import PriceHistoryParser


class TestParseSortedSetEntry:
    """Tests for PriceHistoryParser.parse_sorted_set_entry."""

    def test_valid_entry(self):
        result = PriceHistoryParser.parse_sorted_set_entry("1700000000|42500.5", 1700000000.0)
        assert result == (1700000000, 42500.5)

    def test_valid_bytes_entry(self):
        result = PriceHistoryParser.parse_sorted_set_entry(b"1700000000|100.0", 1700000000.0)
        assert result == (1700000000, 100.0)

    def test_zero_price_returns_none(self):
        result = PriceHistoryParser.parse_sorted_set_entry("1700000000|0.0", 1700000000.0)
        assert result is None

    def test_negative_price_returns_none(self):
        result = PriceHistoryParser.parse_sorted_set_entry("1700000000|-5.0", 1700000000.0)
        assert result is None

    def test_invalid_format_returns_none(self):
        result = PriceHistoryParser.parse_sorted_set_entry("bad_data", 1700000000.0)
        assert result is None

    def test_non_numeric_value_returns_none(self):
        result = PriceHistoryParser.parse_sorted_set_entry("1700000000|abc", 1700000000.0)
        assert result is None
