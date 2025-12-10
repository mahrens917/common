"""Tests for the parsing utilities."""

import json

import orjson
import pytest

from common import parsing_utils


def test_safe_json_loads_success():
    assert parsing_utils.safe_json_loads('{"key": 1}') == {"key": 1}


def test_safe_json_loads_returns_otherwise_on_error():
    expected = {"fallback_val": True}
    assert parsing_utils.safe_json_loads("not json", otherwise=expected) is expected
    assert parsing_utils.safe_json_loads("", otherwise=expected) is expected


def test_safe_orjson_loads_success():
    payload = orjson.dumps({"k": "v"})
    assert parsing_utils.safe_orjson_loads(payload) == {"k": "v"}


def test_safe_orjson_loads_handles_errors():
    expected = []
    assert parsing_utils.safe_orjson_loads(b"", otherwise=expected) is expected
    assert parsing_utils.safe_orjson_loads(b"{bad}", otherwise=expected) is expected


def test_safe_int_parse_handles_variants():
    assert parsing_utils.safe_int_parse("10") == 10
    assert parsing_utils.safe_int_parse("10.5") == 10
    assert parsing_utils.safe_int_parse(5) == 5
    assert parsing_utils.safe_int_parse("", otherwise=-1) == -1


def test_safe_float_parse_limits_nan_inf():
    assert parsing_utils.safe_float_parse("123.5") == 123.5
    assert parsing_utils.safe_float_parse("nan", otherwise=None) is None
    assert parsing_utils.safe_float_parse("inf", otherwise=None) is None
    assert parsing_utils.safe_float_parse("inf", allow_nan_inf=True) == float("inf")


def test_safe_bool_parse_variants():
    assert parsing_utils.safe_bool_parse("true") is True
    assert parsing_utils.safe_bool_parse("no") is False
    assert parsing_utils.safe_bool_parse(0) is False
    assert parsing_utils.safe_bool_parse(None, otherwise=True) is True
