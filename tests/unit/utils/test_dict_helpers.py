import pytest

from src.common.utils.dict_helpers import get_bool, get_str


def test_get_str_handles_missing_and_none():
    assert get_str(None, "key", "fallback") == "fallback"
    assert get_str({}, "key", "fallback") == "fallback"
    assert get_str({"key": None}, "key", "fallback") == "fallback"


def test_get_str_coerces_to_string():
    assert get_str({"key": 123}, "key") == "123"
    assert get_str({"key": "value"}, "key") == "value"


@pytest.mark.parametrize(
    "mapping, expected",
    [
        (None, False),
        ({}, False),
        ({"flag": None}, True),
    ],
)
def test_get_bool_defaults(mapping, expected):
    assert get_bool(mapping, "flag", default=expected) is expected


def test_get_bool_coerces_values():
    assert get_bool({"flag": True}, "flag") is True
    assert get_bool({"flag": False}, "flag") is False
    assert get_bool({"flag": "true"}, "flag") is True
    assert get_bool({"flag": "TRUE"}, "flag") is True
    assert get_bool({"flag": "nope"}, "flag") is False
