"""Unit tests for validation module (validation.py)."""

from __future__ import annotations

import math

import pytest

from common.data_models.micro_price_helpers.validation import (
    MicroPriceValidator,
    get_validation_errors,
    validate_basic_option_data,
    validate_mathematical_relationships,
    validate_micro_price_calculations,
    validate_micro_price_constraints,
)
from common.data_models.micro_price_helpers.validation_params import (
    BasicOptionData,
    MathematicalRelationships,
    ValidationErrorParams,
)


class TestValidateBasicOptionData:
    """Tests for validate_basic_option_data function."""

    def test_valid_params(self) -> None:
        params = BasicOptionData(
            strike=100.0,
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
        )
        validate_basic_option_data(params)

    def test_invalid_params_raises(self) -> None:
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


class TestValidateMicroPriceCalculations:
    """Tests for validate_micro_price_calculations function."""

    def test_valid_values(self) -> None:
        validate_micro_price_calculations(1.0, 0.5, 50.0)

    def test_invalid_values_raises(self) -> None:
        with pytest.raises(TypeError):
            validate_micro_price_calculations(-1.0, 0.5, 50.0)


class TestValidateMathematicalRelationships:
    """Tests for validate_mathematical_relationships function."""

    def test_valid_relationships(self) -> None:
        bid, ask = 10.0, 15.0
        spread = ask - bid
        bid_size, ask_size = 10.0, 10.0
        total = bid_size + ask_size
        i_raw = bid_size / total
        p_raw = (bid * ask_size + ask * bid_size) / total
        rel_spread = spread / p_raw
        g = math.log(spread)
        h = math.log(i_raw / (1 - i_raw))

        params = MathematicalRelationships(
            best_bid=bid,
            best_ask=ask,
            best_bid_size=bid_size,
            best_ask_size=ask_size,
            absolute_spread=spread,
            relative_spread=rel_spread,
            i_raw=i_raw,
            p_raw=p_raw,
            g=g,
            h=h,
        )
        validate_mathematical_relationships(params)

    def test_invalid_spread_raises(self) -> None:
        params = MathematicalRelationships(
            best_bid=10.0,
            best_ask=15.0,
            best_bid_size=None,
            best_ask_size=None,
            absolute_spread=999.0,
            relative_spread=0.1,
            i_raw=0.5,
            p_raw=12.5,
            g=0.0,
            h=0.0,
        )
        with pytest.raises(ValueError):
            validate_mathematical_relationships(params)


class TestValidateMicroPriceConstraints:
    """Tests for validate_micro_price_constraints function."""

    def test_valid_returns_true(self) -> None:
        result = validate_micro_price_constraints(5.0, 15.0, 10.0, 0.5, 10.0)
        assert result is True

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_micro_price_constraints(5.0, 15.0, -1.0, 0.5, 10.0)


class TestGetValidationErrors:
    """Tests for get_validation_errors function."""

    def test_returns_list(self) -> None:
        params = ValidationErrorParams(
            best_bid=0.5,
            best_ask=1.0,
            best_bid_size=10.0,
            best_ask_size=20.0,
            option_type="call",
            absolute_spread=0.5,
            i_raw=0.5,
            p_raw=0.75,
        )
        result = get_validation_errors(params)
        assert isinstance(result, list)


class TestMicroPriceValidatorClass:
    """Tests for MicroPriceValidator class."""

    def test_numerical_tolerance(self) -> None:
        assert MicroPriceValidator.NUMERICAL_TOLERANCE == 0.01

    def test_static_methods_accessible(self) -> None:
        assert callable(MicroPriceValidator.validate_basic_option_data)
        assert callable(MicroPriceValidator.validate_micro_price_calculations)
        assert callable(MicroPriceValidator.validate_mathematical_relationships)
        assert callable(MicroPriceValidator.validate_micro_price_constraints)
        assert callable(MicroPriceValidator.get_validation_errors)
