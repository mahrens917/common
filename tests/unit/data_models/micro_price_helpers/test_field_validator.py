"""Unit tests for field_validator module."""

from __future__ import annotations

import pytest

from common.data_models.micro_price_helpers.field_validator import (
    validate_basic_option_data,
    validate_discount_factor,
    validate_forward_price,
    validate_option_type,
    validate_prices,
    validate_sizes,
    validate_strike,
)
from common.data_models.micro_price_helpers.validation_params import BasicOptionData


class TestValidateStrike:
    """Tests for validate_strike."""

    def test_accepts_positive(self) -> None:
        validate_strike(100.0)

    def test_rejects_zero(self) -> None:
        with pytest.raises(TypeError, match="Strike price must be positive"):
            validate_strike(0.0)

    def test_rejects_negative(self) -> None:
        with pytest.raises(TypeError, match="Strike price must be positive"):
            validate_strike(-1.0)


class TestValidatePrices:
    """Tests for validate_prices."""

    def test_accepts_valid(self) -> None:
        validate_prices(0.5, 1.0)

    def test_rejects_negative_bid(self) -> None:
        with pytest.raises(ValueError, match="Bid price cannot be negative"):
            validate_prices(-0.1, 1.0)

    def test_rejects_negative_ask(self) -> None:
        with pytest.raises(ValueError, match="Ask price cannot be negative"):
            validate_prices(0.5, -0.1)

    def test_rejects_ask_below_bid(self) -> None:
        with pytest.raises(TypeError, match="Ask price.*must be >= bid price"):
            validate_prices(1.0, 0.5)


class TestValidateSizes:
    """Tests for validate_sizes."""

    def test_accepts_none(self) -> None:
        validate_sizes(None, None)

    def test_accepts_positive(self) -> None:
        validate_sizes(10.0, 20.0)

    def test_rejects_negative_bid_size(self) -> None:
        with pytest.raises(ValueError, match="Bid size cannot be negative"):
            validate_sizes(-1.0, 10.0)

    def test_rejects_negative_ask_size(self) -> None:
        with pytest.raises(ValueError, match="Ask size cannot be negative"):
            validate_sizes(10.0, -1.0)


class TestValidateOptionType:
    """Tests for validate_option_type."""

    def test_accepts_call(self) -> None:
        validate_option_type("call")

    def test_accepts_put(self) -> None:
        validate_option_type("put")

    def test_rejects_other(self) -> None:
        with pytest.raises(TypeError, match="Option type must be 'call' or 'put'"):
            validate_option_type("future")


class TestValidateForwardPrice:
    """Tests for validate_forward_price."""

    def test_accepts_positive(self) -> None:
        validate_forward_price(100.0)

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="Forward price must be positive"):
            validate_forward_price(0.0)


class TestValidateDiscountFactor:
    """Tests for validate_discount_factor."""

    def test_accepts_positive(self) -> None:
        validate_discount_factor(0.99)

    def test_rejects_zero(self) -> None:
        with pytest.raises(ValueError, match="Discount factor must be positive"):
            validate_discount_factor(0.0)


class TestValidateBasicOptionData:
    """Tests for validate_basic_option_data."""

    def test_valid_data(self) -> None:
        params = BasicOptionData(
            strike=100.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
            forward_price=102.0,
            discount_factor=0.99,
        )
        validate_basic_option_data(params)

    def test_valid_without_optional_fields(self) -> None:
        params = BasicOptionData(
            strike=100.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=None,
            best_ask_size=None,
            option_type="put",
        )
        validate_basic_option_data(params)

    def test_rejects_invalid_strike(self) -> None:
        params = BasicOptionData(
            strike=-1.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=None,
            best_ask_size=None,
            option_type="call",
        )
        with pytest.raises(TypeError):
            validate_basic_option_data(params)

    def test_validates_forward_price_when_provided(self) -> None:
        params = BasicOptionData(
            strike=100.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=None,
            best_ask_size=None,
            option_type="call",
            forward_price=0.0,
        )
        with pytest.raises(ValueError, match="Forward price must be positive"):
            validate_basic_option_data(params)

    def test_validates_discount_factor_when_provided(self) -> None:
        params = BasicOptionData(
            strike=100.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=None,
            best_ask_size=None,
            option_type="call",
            discount_factor=0.0,
        )
        with pytest.raises(ValueError, match="Discount factor must be positive"):
            validate_basic_option_data(params)
