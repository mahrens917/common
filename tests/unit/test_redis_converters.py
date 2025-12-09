import pytest

from src.common.redis_protocol.converters import coerce_float, decode_redis_hash, decode_redis_value

_CONST_42 = 42


def test_decode_redis_value_leaves_non_bytes():
    assert decode_redis_value(42) == _CONST_42
    assert decode_redis_value("hello") == "hello"
    assert decode_redis_value(b"world") == "world"


def test_decode_redis_hash_decodes_keys_and_values():
    raw = {b"foo": b"123", 2: b"bar"}
    decoded = decode_redis_hash(raw)
    assert decoded == {"foo": "123", "2": "bar"}


@pytest.mark.parametrize(
    "value,expected",
    [
        (" 1.5 ", 1.5),
        (b"2.5", 2.5),
        (3, 3.0),
        (None, None),
        ("null", None),
    ],
)
def test_coerce_float_allows_nulls(value, expected):
    assert coerce_float(value) == expected


def test_coerce_float_raises_when_disallowed():
    with pytest.raises(ValueError):
        coerce_float(None, allow_none=False)

    with pytest.raises(ValueError):
        coerce_float("bad", allow_none=False)
