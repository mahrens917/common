"""Unit tests for ConstraintValidator class."""

from __future__ import annotations

import pytest

from common.data_models.micro_price_helpers.constraint_validator import ConstraintValidator


class TestValidateSpreadConstraint:
    """Tests for validate_spread_constraint."""

    def test_accepts_zero(self) -> None:
        ConstraintValidator.validate_spread_constraint(0.0)

    def test_accepts_positive(self) -> None:
        ConstraintValidator.validate_spread_constraint(1.5)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="Spread constraint violated"):
            ConstraintValidator.validate_spread_constraint(-0.1)


class TestValidateIntensityConstraint:
    """Tests for validate_intensity_constraint."""

    def test_accepts_zero(self) -> None:
        ConstraintValidator.validate_intensity_constraint(0.0)

    def test_accepts_one(self) -> None:
        ConstraintValidator.validate_intensity_constraint(1.0)

    def test_accepts_midpoint(self) -> None:
        ConstraintValidator.validate_intensity_constraint(0.5)

    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="Intensity constraint violated"):
            ConstraintValidator.validate_intensity_constraint(-0.1)

    def test_rejects_above_one(self) -> None:
        with pytest.raises(ValueError, match="Intensity constraint violated"):
            ConstraintValidator.validate_intensity_constraint(1.1)


class TestValidateMicroPriceBounds:
    """Tests for validate_micro_price_bounds."""

    def test_accepts_in_range(self) -> None:
        ConstraintValidator.validate_micro_price_bounds(10.0, 20.0, 15.0)

    def test_accepts_at_bid(self) -> None:
        ConstraintValidator.validate_micro_price_bounds(10.0, 20.0, 10.0)

    def test_accepts_at_ask(self) -> None:
        ConstraintValidator.validate_micro_price_bounds(10.0, 20.0, 20.0)

    def test_rejects_below_bid(self) -> None:
        with pytest.raises(ValueError, match="Micro price constraint violated"):
            ConstraintValidator.validate_micro_price_bounds(10.0, 20.0, 5.0)

    def test_rejects_above_ask(self) -> None:
        with pytest.raises(ValueError, match="Micro price constraint violated"):
            ConstraintValidator.validate_micro_price_bounds(10.0, 20.0, 25.0)


class TestValidateBidReconstruction:
    """Tests for validate_bid_reconstruction."""

    def test_accepts_matching(self) -> None:
        # p_raw - i_raw * spread = best_bid → 10 - 0.5*10 = 5 → bid=5
        ConstraintValidator.validate_bid_reconstruction(5.0, 10.0, 0.5, 10.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Bid reconstruction constraint violated"):
            ConstraintValidator.validate_bid_reconstruction(99.0, 10.0, 0.5, 10.0)


class TestValidateAskReconstruction:
    """Tests for validate_ask_reconstruction."""

    def test_accepts_matching(self) -> None:
        # p_raw + (1 - i_raw) * spread = best_ask → 10 + 0.5*10 = 15 → ask=15
        ConstraintValidator.validate_ask_reconstruction(15.0, 10.0, 0.5, 10.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Ask reconstruction constraint violated"):
            ConstraintValidator.validate_ask_reconstruction(99.0, 10.0, 0.5, 10.0)


class TestValidateMicroPriceConstraints:
    """Tests for validate_micro_price_constraints."""

    def test_valid_constraints_returns_true(self) -> None:
        # best_bid=5, best_ask=15, spread=10, i_raw=0.5
        # p_raw = bid + i_raw*spread = 5 + 5 = 10
        result = ConstraintValidator.validate_micro_price_constraints(5.0, 15.0, 10.0, 0.5, 10.0)
        assert result is True

    def test_rejects_invalid_spread(self) -> None:
        with pytest.raises(ValueError):
            ConstraintValidator.validate_micro_price_constraints(5.0, 15.0, -1.0, 0.5, 10.0)
