import math

import pytest

from common.exceptions import ValidationError
from common.redis_protocol.kalshi_store import utils_coercion as utils


def test_bool_and_numeric_defaults():
    assert utils.bool_or_default("true", False, parse_strings=True) is True
    assert utils.int_or_default("3") == 3
    assert math.isclose(utils.float_or_default("1.5"), 1.5)


def test_coercion_helpers():
    assert utils.coerce_mapping({"a": 1}) == {"a": 1}
    assert utils.coerce_mapping(["a"]) == {}
    assert utils.coerce_sequence(None) == []
    assert utils.string_or_default(None, fallback_value="x") == "x"


def test_optional_float_and_validation():
    assert utils.to_optional_float("2.5", context="test") == 2.5
    assert utils.to_optional_float("", context="test") is None
    with pytest.raises(RuntimeError):
        utils.to_optional_float("bad", context="test")


def test_convert_numeric_field_and_probability_formatting():
    assert utils.convert_numeric_field(None) is None
    assert utils.convert_numeric_field("2.0") == 2.0
    assert math.isnan(utils.convert_numeric_field("nan"))
    formatted = utils.format_probability_value(0.1234567890123)
    assert formatted.startswith("0.123456789")
    assert "." in formatted and not formatted.endswith(".")


def test_sync_top_of_book_fields():
    snapshot = {"yes_bids": {"10": 5}, "yes_asks": {"12": 7}}
    utils.sync_top_of_book_fields(snapshot)
    assert snapshot["yes_bid"] == "10.0"
    assert snapshot["yes_ask"] == "12.0"
    assert snapshot["yes_bid_size"] == "5"
    assert snapshot["yes_ask_size"] == "7"
