"""Tests for numerical_validators module."""

import math

import pytest

from common.validation_helpers.exceptions import ValidationError
from common.validation_helpers.numerical_validators import NumericalValidators


class TestValidateProbabilityValue:
    """Tests for validate_probability_value method."""

    def test_valid_probability_zero(self) -> None:
        """Test probability of 0 is valid."""
        assert NumericalValidators.validate_probability_value(0.0) is True

    def test_valid_probability_one(self) -> None:
        """Test probability of 1 is valid."""
        assert NumericalValidators.validate_probability_value(1.0) is True

    def test_valid_probability_middle(self) -> None:
        """Test probability of 0.5 is valid."""
        assert NumericalValidators.validate_probability_value(0.5) is True

    def test_probability_nan_raises(self) -> None:
        """Test NaN probability raises error."""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            NumericalValidators.validate_probability_value(float("nan"))

    def test_probability_inf_raises(self) -> None:
        """Test infinite probability raises error."""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            NumericalValidators.validate_probability_value(float("inf"))

    def test_probability_negative_raises(self) -> None:
        """Test negative probability raises error."""
        with pytest.raises(ValidationError, match="must be in range"):
            NumericalValidators.validate_probability_value(-0.1)

    def test_probability_above_one_raises(self) -> None:
        """Test probability above 1 raises error."""
        with pytest.raises(ValidationError, match="must be in range"):
            NumericalValidators.validate_probability_value(1.1)

    def test_probability_non_numeric_raises(self) -> None:
        """Test non-numeric raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            NumericalValidators.validate_probability_value("0.5")


class TestValidateStrikePrice:
    """Tests for validate_strike_price method."""

    def test_valid_strike_price(self) -> None:
        """Test valid strike price passes."""
        assert NumericalValidators.validate_strike_price(100.0) is True

    def test_valid_small_strike_price(self) -> None:
        """Test small positive strike price passes."""
        assert NumericalValidators.validate_strike_price(0.01) is True


class TestValidateMarketPrice:
    """Tests for validate_market_price method."""

    def test_valid_market_price(self) -> None:
        """Test valid market price passes."""
        assert NumericalValidators.validate_market_price(50.0) is True

    def test_valid_zero_price(self) -> None:
        """Test zero price is valid."""
        assert NumericalValidators.validate_market_price(0.0) is True

    def test_price_nan_raises(self) -> None:
        """Test NaN price raises error."""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            NumericalValidators.validate_market_price(float("nan"))

    def test_price_inf_raises(self) -> None:
        """Test infinite price raises error."""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            NumericalValidators.validate_market_price(float("inf"))

    def test_negative_price_raises(self) -> None:
        """Test negative price raises error."""
        with pytest.raises(ValidationError, match="cannot be negative"):
            NumericalValidators.validate_market_price(-1.0)

    def test_kalshi_price_exceeds_max(self) -> None:
        """Test Kalshi price exceeding max raises error."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            NumericalValidators.validate_market_price(150.0, price_type="kalshi")

    def test_yes_price_exceeds_max(self) -> None:
        """Test yes price exceeding max raises error."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            NumericalValidators.validate_market_price(150.0, price_type="yes")

    def test_no_price_exceeds_max(self) -> None:
        """Test no price exceeding max raises error."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            NumericalValidators.validate_market_price(150.0, price_type="no")

    def test_general_price_can_exceed_kalshi_max(self) -> None:
        """Test general price type allows higher values."""
        assert NumericalValidators.validate_market_price(150.0, price_type="general") is True

    def test_price_non_numeric_raises(self) -> None:
        """Test non-numeric raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            NumericalValidators.validate_market_price("50")


class TestValidateNumericalRange:
    """Tests for validate_numerical_range method."""

    def test_value_in_range(self) -> None:
        """Test value within range is valid."""
        assert NumericalValidators.validate_numerical_range(50.0, 0.0, 100.0) is True

    def test_value_at_min(self) -> None:
        """Test value at minimum is valid."""
        assert NumericalValidators.validate_numerical_range(0.0, 0.0, 100.0) is True

    def test_value_at_max(self) -> None:
        """Test value at maximum is valid."""
        assert NumericalValidators.validate_numerical_range(100.0, 0.0, 100.0) is True

    def test_value_nan_raises(self) -> None:
        """Test NaN value raises error."""
        with pytest.raises(ValidationError, match="cannot be NaN"):
            NumericalValidators.validate_numerical_range(float("nan"), 0.0, 100.0)

    def test_value_inf_raises(self) -> None:
        """Test infinite value raises error."""
        with pytest.raises(ValidationError, match="cannot be infinite"):
            NumericalValidators.validate_numerical_range(float("inf"), 0.0, 100.0)

    def test_value_below_min_raises(self) -> None:
        """Test value below min raises error."""
        with pytest.raises(ValidationError, match="must be in range"):
            NumericalValidators.validate_numerical_range(-1.0, 0.0, 100.0)

    def test_value_above_max_raises(self) -> None:
        """Test value above max raises error."""
        with pytest.raises(ValidationError, match="must be in range"):
            NumericalValidators.validate_numerical_range(101.0, 0.0, 100.0)

    def test_custom_value_name_in_error(self) -> None:
        """Test custom value name appears in error."""
        with pytest.raises(ValidationError, match="temperature"):
            NumericalValidators.validate_numerical_range(200.0, 0.0, 100.0, "temperature")

    def test_non_numeric_value_raises(self) -> None:
        """Test non-numeric raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            NumericalValidators.validate_numerical_range("50", 0.0, 100.0)
