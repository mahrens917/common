from unittest.mock import Mock

import pytest

from common.redis_protocol.atomic_redis_operations_helpers.data_converter import (
    DataConverter,
    RedisDataValidationError,
)


class TestDataConverter:
    def test_convert_market_payload_success(self):
        converter = DataConverter(max_retries=3)
        raw_data = {"price": "10.5", "volume": "100", "last_update": "timestamp", "symbol": "TEST"}

        result = converter.convert_market_payload(raw_data, "key", 0)

        assert result["price"] == 10.5
        assert isinstance(result["price"], float)
        assert result["volume"] == 100
        assert isinstance(result["volume"], int)
        assert result["last_update"] == "timestamp"
        assert result["symbol"] == "TEST"

    def test_convert_market_payload_failure(self):
        converter = DataConverter(max_retries=3)
        raw_data = {"price": "invalid"}  # Should be numeric if we assume logic?

        # The current logic tries to coerce everything not in exclusion list.
        # But _coerce_numeric_value returns original value if it fails to be int/float?
        # Wait, let's check _coerce_numeric_value implementation again.

        # if "." in string_value: return float(string_value) -> raises ValueError if not float
        # if string_value.isdigit(): return int(string_value)
        # return value

        # So "invalid" returns "invalid". It doesn't raise exception.

        result = converter.convert_market_payload(raw_data, "key", 0)
        assert result["price"] == "invalid"

    def test_convert_market_payload_float_error(self):
        # To trigger ValueError in float(), we need "." but invalid float
        converter = DataConverter(max_retries=3)
        raw_data = {"price": "10.invalid"}

        with pytest.raises(RedisDataValidationError):
            converter.convert_market_payload(raw_data, "key", 0)

    def test_coerce_numeric_value_edge_cases(self):
        converter = DataConverter(max_retries=3)
        assert converter._coerce_numeric_value("10.") == 10.0
        assert converter._coerce_numeric_value(".5") == 0.5
        assert converter._coerce_numeric_value("123") == 123
        assert converter._coerce_numeric_value("abc") == "abc"
