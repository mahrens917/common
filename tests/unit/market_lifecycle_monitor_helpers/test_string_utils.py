from __future__ import annotations

from common.market_lifecycle_monitor_helpers.string_utils import coerce_optional_str


def test_coerce_optional_str_returns_empty_string_when_missing() -> None:
    assert coerce_optional_str({}, "field") == ""
    assert coerce_optional_str({"field": None}, "field") == ""


def test_coerce_optional_str_coerces_value_to_string() -> None:
    assert coerce_optional_str({"field": 123}, "field") == "123"
    assert coerce_optional_str({"field": "abc"}, "field") == "abc"
