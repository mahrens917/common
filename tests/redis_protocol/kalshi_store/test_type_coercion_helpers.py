import pytest

from common.redis_protocol.kalshi_store.utils_coercion_helpers import type_coercion as tc


@pytest.mark.parametrize(
    "value,expected",
    [
        ({"a": 1}, {"a": 1}),
        ([("a", 1)], {}),
        ("not-mapping", {}),
    ],
)
def test_coerce_mapping(value, expected):
    assert tc.coerce_mapping(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ([1, 2], [1, 2]),
        ((3, 4), [3, 4]),
        ("ab", ["a", "b"]),
        (None, []),
    ],
)
def test_coerce_sequence(value, expected):
    assert tc.coerce_sequence(value) == expected


def test_string_int_float_bool_defaults():
    assert tc.string_or_default(b"bytes") == "bytes"
    assert tc.string_or_default(None, default="x") == "x"
    assert tc.int_or_default("5") == 5
    assert tc.float_or_default("1.25") == 1.25
    assert tc.bool_or_default("yes", False, parse_strings=True) is True
    with pytest.raises(ValueError):
        tc.float_or_default(None, raise_on_error=True)
