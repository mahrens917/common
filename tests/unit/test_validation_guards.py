"""Tests for the validation guard helpers."""

from datetime import date, datetime, timezone

import pytest

from common.validation_guards import (
    require,
    require_date,
    require_datetime,
    require_instance,
    require_keys,
    require_non_empty_string,
    require_non_negative,
    require_optional_instance,
    require_percentage,
)


def test_require_passes():
    require(True, RuntimeError("fail"))


def test_require_fails():
    with pytest.raises(ValueError):
        require(False, ValueError("bad"))


def test_require_instance_accepts():
    require_instance("text", str, "field")


def test_require_instance_rejects():
    with pytest.raises(TypeError):
        require_instance(1, str, "field")


def test_require_optional_instance_accepts_none():
    require_optional_instance(None, str, "field")


def test_require_optional_instance_checks_type():
    with pytest.raises(TypeError):
        require_optional_instance(1, str, "field")


def test_require_non_empty_string_valid():
    require_non_empty_string("value", "field")


def test_require_non_empty_string_invalid():
    with pytest.raises(ValueError):
        require_non_empty_string("   ", "field")


def test_require_date_accepts_date():
    require_date(date.today(), "field")


def test_require_date_rejects():
    with pytest.raises(TypeError):
        require_date("2023-01-01", "field")


def test_require_datetime_accepts_datetime():
    require_datetime(datetime.now(timezone.utc), "field")


def test_require_non_negative_accepts():
    require_non_negative(0, "count")


def test_require_non_negative_rejects():
    with pytest.raises(ValueError):
        require_non_negative(-1, "count")


def test_require_percentage_accepts():
    require_percentage(0.5, "pct")


def test_require_percentage_rejects():
    with pytest.raises(TypeError):
        require_percentage(2.0, "pct")


def test_require_keys_all_present():
    require_keys({"a": 1, "b": 2}, ["a"], "prefix")


def test_require_keys_missing():
    with pytest.raises(KeyError):
        require_keys({"a": 1}, ["b"], "prefix")
