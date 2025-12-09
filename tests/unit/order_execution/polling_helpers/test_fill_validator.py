"""Tests for order execution fill validators."""

from unittest.mock import MagicMock

import pytest

from src.common.order_execution.polling_helpers.fill_validator import (
    validate_fill_count,
    validate_fill_price,
    validate_fill_side,
)
from src.common.trading_exceptions import KalshiOrderPollingError


@pytest.mark.parametrize(
    "fill,count",
    [
        ({"count": "5"}, 5),
        ({"count": 3}, 3),
    ],
)
def test_validate_fill_count_accepts_ints(fill, count):
    assert validate_fill_count(fill, order_id="order", operation_name="op") == count


def test_validate_fill_count_missing_raises():
    with pytest.raises(KalshiOrderPollingError, match="Fill missing 'count' value"):
        validate_fill_count({}, "order", "op")


@pytest.mark.parametrize("invalid", ["abc", None])
def test_validate_fill_count_invalid_type_raises(invalid):
    with pytest.raises(KalshiOrderPollingError, match="Invalid fill count"):
        validate_fill_count({"count": invalid}, "order", "op")


def test_validate_fill_count_non_positive_raises():
    with pytest.raises(KalshiOrderPollingError, match="non-positive fill count"):
        validate_fill_count({"count": 0}, "order", "op")


def test_validate_fill_side_accepts_valid_side():
    assert validate_fill_side({"side": "yes"}, "order", "op") == "yes"


def test_validate_fill_side_missing_raises():
    with pytest.raises(KalshiOrderPollingError, match="Fill missing 'side'"):
        validate_fill_side({}, "order", "op")


def test_validate_fill_side_invalid_value():
    with pytest.raises(KalshiOrderPollingError, match="missing valid side"):
        validate_fill_side({"side": "maybe"}, "order", "op")


def test_validate_fill_price_accepts_yes_side():
    assert validate_fill_price({"yes_price": 10}, "yes", "order", "op") == 10


def test_validate_fill_price_invalid_missing():
    with pytest.raises(KalshiOrderPollingError, match="Fill missing yes_price"):
        validate_fill_price({}, "yes", "order", "op")


def test_validate_fill_price_invalid_value():
    with pytest.raises(KalshiOrderPollingError, match="Invalid price in fill"):
        validate_fill_price({"yes_price": "bad"}, "yes", "order", "op")
