"""Unit tests for RelationshipValidator class."""

from __future__ import annotations

import math

import pytest

from common.data_models.micro_price_helpers.relationship_validator import RelationshipValidator


class TestValidateSpreadRelationship:
    """Tests for validate_spread_relationship."""

    def test_accepts_matching(self) -> None:
        RelationshipValidator.validate_spread_relationship(10.0, 15.0, 5.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Absolute spread"):
            RelationshipValidator.validate_spread_relationship(10.0, 15.0, 9.0)


class TestValidateRelativeSpread:
    """Tests for validate_relative_spread."""

    def test_accepts_matching(self) -> None:
        # relative_spread = absolute_spread / p_raw = 2.0 / 10.0 = 0.2
        RelationshipValidator.validate_relative_spread(2.0, 0.2, 10.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Relative spread"):
            RelationshipValidator.validate_relative_spread(2.0, 0.9, 10.0)


class TestValidateIntensityCalculation:
    """Tests for validate_intensity_calculation."""

    def test_skips_with_none_sizes(self) -> None:
        RelationshipValidator.validate_intensity_calculation(None, None, 0.5)

    def test_skips_with_one_none(self) -> None:
        RelationshipValidator.validate_intensity_calculation(10.0, None, 0.5)

    def test_accepts_matching(self) -> None:
        # i_raw = bid_size / (bid_size + ask_size) = 10 / (10+10) = 0.5
        RelationshipValidator.validate_intensity_calculation(10.0, 10.0, 0.5)

    def test_skips_when_total_volume_zero(self) -> None:
        RelationshipValidator.validate_intensity_calculation(0.0, 0.0, 0.5)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="I_raw"):
            RelationshipValidator.validate_intensity_calculation(10.0, 10.0, 0.9)


class TestValidateMicroPriceCalculation:
    """Tests for validate_micro_price_calculation."""

    def test_skips_with_none_sizes(self) -> None:
        RelationshipValidator.validate_micro_price_calculation(10.0, 15.0, None, None, 12.0)

    def test_accepts_matching(self) -> None:
        # p_raw = (bid*ask_size + ask*bid_size) / total = (10*10 + 15*10) / 20 = 250/20 = 12.5
        RelationshipValidator.validate_micro_price_calculation(10.0, 15.0, 10.0, 10.0, 12.5)

    def test_skips_when_total_volume_zero(self) -> None:
        RelationshipValidator.validate_micro_price_calculation(10.0, 15.0, 0.0, 0.0, 12.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="p_raw"):
            RelationshipValidator.validate_micro_price_calculation(10.0, 15.0, 10.0, 10.0, 99.0)


class TestValidateGTransformation:
    """Tests for validate_g_transformation."""

    def test_accepts_matching(self) -> None:
        spread = 5.0
        g = math.log(spread)
        RelationshipValidator.validate_g_transformation(spread, g)

    def test_skips_non_positive_spread(self) -> None:
        RelationshipValidator.validate_g_transformation(0.0, -99.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="g"):
            RelationshipValidator.validate_g_transformation(5.0, 999.0)


class TestValidateHTransformation:
    """Tests for validate_h_transformation."""

    def test_accepts_matching(self) -> None:
        i_raw = 0.6
        h = math.log(i_raw / (1 - i_raw))
        RelationshipValidator.validate_h_transformation(i_raw, h)

    def test_skips_boundary_i_raw_zero(self) -> None:
        RelationshipValidator.validate_h_transformation(0.0, -999.0)

    def test_skips_boundary_i_raw_one(self) -> None:
        RelationshipValidator.validate_h_transformation(1.0, 999.0)

    def test_rejects_mismatch(self) -> None:
        with pytest.raises(ValueError, match="h"):
            RelationshipValidator.validate_h_transformation(0.5, 999.0)
