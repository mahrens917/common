import unittest

from common.strike_helpers import (
    check_strike_in_range,
    decode_redis_key,
    extract_strike_from_key,
    parse_strike_value,
)


class TestStrikeParser(unittest.TestCase):
    def test_decode_redis_key(self):
        assert decode_redis_key(b"key") == "key"
        assert decode_redis_key("key") == "key"
        # Test decoding error handling
        # Invalid utf-8 sequence
        invalid_bytes = b"\x80"
        assert decode_redis_key(invalid_bytes) is None

    def test_extract_strike_from_key(self):
        key = "probabilities:BTC:TYPE:TIMESTAMP:50000"
        assert extract_strike_from_key(key) == "50000"

        malformed = "probabilities:BTC:TYPE:TIMESTAMP"
        assert extract_strike_from_key(malformed) is None

    def test_parse_strike_value(self):
        assert parse_strike_value("50000") == 50000.0
        assert parse_strike_value("50000.5") == 50000.5
        assert parse_strike_value("invalid") is None

    def test_check_strike_in_range_single(self):
        # In range
        assert check_strike_in_range("55000", 50000, 60000) is True
        # Below range
        assert check_strike_in_range("40000", 50000, 60000) is False
        # Above range
        assert check_strike_in_range("70000", 50000, 60000) is False
        # Invalid
        assert check_strike_in_range("invalid", 50000, 60000) is False

    def test_check_strike_in_range_interval(self):
        # Fully inside
        assert check_strike_in_range("52000-58000", 50000, 60000) is True
        # Overlap low
        assert check_strike_in_range("40000-55000", 50000, 60000) is True
        # Overlap high
        assert check_strike_in_range("55000-65000", 50000, 60000) is True
        # Fully outside low
        assert check_strike_in_range("40000-45000", 50000, 60000) is False
        # Fully outside high
        assert check_strike_in_range("65000-70000", 50000, 60000) is False
        # Encompassing
        assert check_strike_in_range("40000-70000", 50000, 60000) is True

    def test_check_strike_in_range_greater_than(self):
        # Threshold inside
        assert check_strike_in_range(">55000", 50000, 60000) is True
        # Threshold below
        assert check_strike_in_range(">40000", 50000, 60000) is True
        # Threshold above
        assert check_strike_in_range(">65000", 50000, 60000) is False
