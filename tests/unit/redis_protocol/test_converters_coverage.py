import math

import pytest

from src.common.redis_protocol.converters import (
    FloatCoercionError,
    coerce_float,
    decode_redis_hash,
    decode_redis_value,
)


class TestConvertersCoverage:
    def test_decode_redis_value(self):
        assert decode_redis_value(b"test") == "test"
        assert decode_redis_value("test") == "test"
        assert decode_redis_value(123) == 123
        assert decode_redis_value(None) is None

    def test_decode_redis_hash(self):
        raw = {b"key1": b"value1", "key2": 123}
        decoded = decode_redis_hash(raw)
        assert decoded["key1"] == "value1"
        assert decoded["key2"] == 123

        # Test non-string key
        raw_mixed = {123: b"val"}
        decoded_mixed = decode_redis_hash(raw_mixed)
        assert decoded_mixed["123"] == "val"

    def test_coerce_float_valid(self):
        assert coerce_float(1.5) == 1.5
        assert coerce_float("1.5") == 1.5
        assert coerce_float(b"1.5") == 1.5
        assert coerce_float(1) == 1.0

    def test_coerce_float_none(self):
        assert coerce_float(None) is None
        assert coerce_float("None") is None
        assert coerce_float("null") is None
        assert coerce_float("") is None

        with pytest.raises(ValueError, match="Cannot coerce None to float"):
            coerce_float(None, allow_none=False)

        with pytest.raises(ValueError, match="Cannot coerce None to float"):
            coerce_float("None", allow_none=False)

    def test_coerce_float_finite(self):
        assert coerce_float(float("inf"), finite_only=False) == float("inf")
        assert coerce_float(float("nan"), finite_only=False) is not None  # nan != nan

        assert coerce_float(float("inf"), finite_only=True) is None
        assert coerce_float(float("nan"), finite_only=True) is None

        with pytest.raises(ValueError, match="Cannot coerce None to float"):
            coerce_float(float("inf"), finite_only=True, allow_none=False)

    def test_coerce_float_invalid(self):
        assert coerce_float("invalid") is None
        with pytest.raises(FloatCoercionError, match="Cannot coerce value to float"):
            coerce_float("invalid", allow_none=False)

    def test_coerce_float_custom_sentinels(self):
        assert coerce_float("N/A", null_sentinels=["N/A"]) is None
