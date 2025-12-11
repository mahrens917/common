"""Unit tests for CalculationValidator class."""

from __future__ import annotations

import pytest

from common.data_models.micro_price_helpers.calculation_validator import (
    CalculationValidator,
)


class TestValidateAbsoluteSpread:
    """Tests for validate_absolute_spread method."""

    def test_accepts_zero(self) -> None:
        """Test that zero absolute spread is valid."""
        CalculationValidator.validate_absolute_spread(0.0)  # Should not raise

    def test_accepts_positive_value(self) -> None:
        """Test that positive absolute spread is valid."""
        CalculationValidator.validate_absolute_spread(1.0)  # Should not raise
        CalculationValidator.validate_absolute_spread(0.5)  # Should not raise
        CalculationValidator.validate_absolute_spread(100.0)  # Should not raise

    def test_rejects_negative_value(self) -> None:
        """Test that negative absolute spread raises TypeError."""
        with pytest.raises(TypeError, match="Absolute spread must be non-negative"):
            CalculationValidator.validate_absolute_spread(-1.0)

        with pytest.raises(TypeError, match="Absolute spread must be non-negative"):
            CalculationValidator.validate_absolute_spread(-0.1)

    def test_error_message_includes_value(self) -> None:
        """Test that error message includes the invalid value."""
        with pytest.raises(TypeError, match="-5.0"):
            CalculationValidator.validate_absolute_spread(-5.0)


class TestValidateIntensity:
    """Tests for validate_intensity method."""

    def test_accepts_zero(self) -> None:
        """Test that intensity of 0 is valid."""
        CalculationValidator.validate_intensity(0.0)  # Should not raise

    def test_accepts_one(self) -> None:
        """Test that intensity of 1 is valid."""
        CalculationValidator.validate_intensity(1.0)  # Should not raise

    def test_accepts_value_in_range(self) -> None:
        """Test that intensity values in [0,1] are valid."""
        CalculationValidator.validate_intensity(0.5)  # Should not raise
        CalculationValidator.validate_intensity(0.25)  # Should not raise
        CalculationValidator.validate_intensity(0.75)  # Should not raise
        CalculationValidator.validate_intensity(0.999)  # Should not raise

    def test_rejects_negative_value(self) -> None:
        """Test that negative intensity raises TypeError."""
        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_intensity(-0.1)

        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_intensity(-1.0)

    def test_rejects_value_greater_than_one(self) -> None:
        """Test that intensity > 1 raises TypeError."""
        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_intensity(1.1)

        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_intensity(2.0)

    def test_error_message_includes_value(self) -> None:
        """Test that error message includes the invalid value."""
        with pytest.raises(TypeError, match="1.5"):
            CalculationValidator.validate_intensity(1.5)


class TestValidateRawMicroPrice:
    """Tests for validate_raw_micro_price method."""

    def test_accepts_positive_value(self) -> None:
        """Test that positive raw micro price is valid."""
        CalculationValidator.validate_raw_micro_price(1.0)  # Should not raise
        CalculationValidator.validate_raw_micro_price(0.1)  # Should not raise
        CalculationValidator.validate_raw_micro_price(100.0)  # Should not raise
        CalculationValidator.validate_raw_micro_price(0.001)  # Should not raise

    def test_rejects_zero(self) -> None:
        """Test that zero raw micro price raises TypeError."""
        with pytest.raises(TypeError, match="Raw micro price.*must be positive"):
            CalculationValidator.validate_raw_micro_price(0.0)

    def test_rejects_negative_value(self) -> None:
        """Test that negative raw micro price raises TypeError."""
        with pytest.raises(TypeError, match="Raw micro price.*must be positive"):
            CalculationValidator.validate_raw_micro_price(-1.0)

        with pytest.raises(TypeError, match="Raw micro price.*must be positive"):
            CalculationValidator.validate_raw_micro_price(-0.1)

    def test_error_message_includes_value(self) -> None:
        """Test that error message includes the invalid value."""
        with pytest.raises(TypeError, match="-5.0"):
            CalculationValidator.validate_raw_micro_price(-5.0)


class TestValidateMicroPriceCalculations:
    """Tests for validate_micro_price_calculations method."""

    def test_accepts_all_valid_parameters(self) -> None:
        """Test that all valid parameters pass validation."""
        CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=0.5, p_raw=50.0)  # Should not raise

    def test_accepts_boundary_values(self) -> None:
        """Test that boundary values pass validation."""
        # absolute_spread = 0
        CalculationValidator.validate_micro_price_calculations(absolute_spread=0.0, i_raw=0.5, p_raw=50.0)  # Should not raise

        # i_raw = 0
        CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=0.0, p_raw=50.0)  # Should not raise

        # i_raw = 1
        CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=1.0, p_raw=50.0)  # Should not raise

        # Very small p_raw
        CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=0.5, p_raw=0.001)  # Should not raise

    def test_rejects_negative_absolute_spread(self) -> None:
        """Test that negative absolute_spread is rejected."""
        with pytest.raises(TypeError, match="Absolute spread must be non-negative"):
            CalculationValidator.validate_micro_price_calculations(absolute_spread=-1.0, i_raw=0.5, p_raw=50.0)

    def test_rejects_intensity_below_zero(self) -> None:
        """Test that i_raw < 0 is rejected."""
        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=-0.1, p_raw=50.0)

    def test_rejects_intensity_above_one(self) -> None:
        """Test that i_raw > 1 is rejected."""
        with pytest.raises(TypeError, match="Raw intensity.*must be in"):
            CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=1.1, p_raw=50.0)

    def test_rejects_zero_raw_micro_price(self) -> None:
        """Test that p_raw = 0 is rejected."""
        with pytest.raises(TypeError, match="Raw micro price.*must be positive"):
            CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=0.5, p_raw=0.0)

    def test_rejects_negative_raw_micro_price(self) -> None:
        """Test that p_raw < 0 is rejected."""
        with pytest.raises(TypeError, match="Raw micro price.*must be positive"):
            CalculationValidator.validate_micro_price_calculations(absolute_spread=1.0, i_raw=0.5, p_raw=-1.0)

    def test_validates_in_correct_order(self) -> None:
        """Test that validation happens in the expected order."""
        # When multiple parameters are invalid, first one should be caught
        with pytest.raises(TypeError, match="Absolute spread"):
            CalculationValidator.validate_micro_price_calculations(
                absolute_spread=-1.0,  # Invalid
                i_raw=2.0,  # Also invalid
                p_raw=-1.0,  # Also invalid
            )

    def test_typical_valid_use_case(self) -> None:
        """Test a typical valid use case with realistic values."""
        CalculationValidator.validate_micro_price_calculations(absolute_spread=2.5, i_raw=0.65, p_raw=48.75)  # Should not raise
