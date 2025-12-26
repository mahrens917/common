"""Tests for price_path_calculator_helpers.expectation_scaler module."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from common.price_path_calculator_helpers.expectation_scaler import ExpectationScaler

# Test constants
EXPECTED_INTERP_SCALED = (50.0, 51.0, 52.0)
FORWARD_INTERP_SCALED = (50.0, 51.0, 52.0)
SIGMA_INTERP_SCALED = (1.0, 1.1, 1.2)
SIGMA_P95_INTERP_SCALED = (2.0, 2.2, 2.4)

EXPECTED_INTERP_NO_SPOT = (100.0, 101.0, 102.0)
FORWARD_INTERP_NO_SPOT = (100.0, 101.0, 102.0)
SIGMA_INTERP_NO_SPOT = (1.0, 1.0, 1.0)
SIGMA_P95_INTERP_NO_SPOT = (2.0, 2.0, 2.0)

EXPECTED_INTERP_ZERO_SPOT = (100.0, 101.0, 102.0)
FORWARD_INTERP_ZERO_SPOT = (100.0, 101.0, 102.0)
SIGMA_INTERP_ZERO_SPOT = (1.0, 1.0, 1.0)
SIGMA_P95_INTERP_ZERO_SPOT = (2.0, 2.0, 2.0)

EXPECTED_INTERP_ZERO_REF = (0.0, 1.0, 2.0)
FORWARD_INTERP_ZERO_REF = (50.0, 51.0, 52.0)
SIGMA_INTERP_ZERO_REF = (1.0, 1.0, 1.0)
SIGMA_P95_INTERP_ZERO_REF = (2.0, 2.0, 2.0)

EXPECTED_INTERP_BOUNDED = (100.0, 100.0, 100.0)
FORWARD_INTERP_BOUNDED = (100.0, 100.0, 100.0)
SIGMA_INTERP_BOUNDED = (0.5, 0.5, 0.5)
SIGMA_P95_INTERP_BOUNDED = (1.0, 1.0, 1.0)


class TestExpectationScalerInit:
    """Tests for ExpectationScaler initialization."""

    def test_stores_sigma_ratios(self) -> None:
        """Test initialization stores sigma ratios."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)

        assert scaler._sigma_min_ratio == 0.01
        assert scaler._sigma_max_ratio == 0.1


class TestExpectationScalerScaleExpectations:
    """Tests for scale_expectations method."""

    def test_scales_with_spot_price(self) -> None:
        """Test scales expectations using spot price."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)
        mock_surface = MagicMock()
        mock_surface.spot_price = 100.0

        expected_interp = np.array(EXPECTED_INTERP_SCALED)
        forward_interp = np.array(FORWARD_INTERP_SCALED)
        sigma_interp = np.array(SIGMA_INTERP_SCALED)
        sigma_p95_interp = np.array(SIGMA_P95_INTERP_SCALED)

        expected_prices, uncertainties = scaler.scale_expectations(
            surface=mock_surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )

        # Spot is 100, expected[0] is 50, so scale_ratio is 2.0
        assert expected_prices[0] == pytest.approx(100.0)
        assert expected_prices[1] == pytest.approx(102.0)
        assert expected_prices[2] == pytest.approx(104.0)

    def test_uses_expected_interp_when_no_spot(self) -> None:
        """Test uses expected_interp when spot_price is None."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)
        mock_surface = MagicMock()
        mock_surface.spot_price = None

        expected_interp = np.array(EXPECTED_INTERP_NO_SPOT)
        forward_interp = np.array(FORWARD_INTERP_NO_SPOT)
        sigma_interp = np.array(SIGMA_INTERP_NO_SPOT)
        sigma_p95_interp = np.array(SIGMA_P95_INTERP_NO_SPOT)

        expected_prices, uncertainties = scaler.scale_expectations(
            surface=mock_surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )

        # No scaling when spot equals reference
        assert expected_prices[0] == pytest.approx(100.0)

    def test_uses_zero_spot_price(self) -> None:
        """Test handles zero spot price."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)
        mock_surface = MagicMock()
        mock_surface.spot_price = 0.0  # Zero spot price

        expected_interp = np.array(EXPECTED_INTERP_ZERO_SPOT)
        forward_interp = np.array(FORWARD_INTERP_ZERO_SPOT)
        sigma_interp = np.array(SIGMA_INTERP_ZERO_SPOT)
        sigma_p95_interp = np.array(SIGMA_P95_INTERP_ZERO_SPOT)

        expected_prices, uncertainties = scaler.scale_expectations(
            surface=mock_surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )

        # Should use expected_interp[0] as spot reference
        assert expected_prices[0] == pytest.approx(100.0)

    def test_handles_zero_reference(self) -> None:
        """Test handles zero reference expectation."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)
        mock_surface = MagicMock()
        mock_surface.spot_price = 100.0

        expected_interp = np.array(EXPECTED_INTERP_ZERO_REF)
        forward_interp = np.array(FORWARD_INTERP_ZERO_REF)
        sigma_interp = np.array(SIGMA_INTERP_ZERO_REF)
        sigma_p95_interp = np.array(SIGMA_P95_INTERP_ZERO_REF)

        expected_prices, uncertainties = scaler.scale_expectations(
            surface=mock_surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )

        # Should use forward[0] as reference when expected[0] is 0
        assert expected_prices[0] == pytest.approx(0.0)

    def test_returns_bounded_uncertainties(self) -> None:
        """Test returns uncertainties bounded by min/max sigma ratios."""
        scaler = ExpectationScaler(sigma_min_ratio=0.01, sigma_max_ratio=0.1)
        mock_surface = MagicMock()
        mock_surface.spot_price = 100.0

        expected_interp = np.array(EXPECTED_INTERP_BOUNDED)
        forward_interp = np.array(FORWARD_INTERP_BOUNDED)
        sigma_interp = np.array(SIGMA_INTERP_BOUNDED)
        sigma_p95_interp = np.array(SIGMA_P95_INTERP_BOUNDED)

        expected_prices, uncertainties = scaler.scale_expectations(
            surface=mock_surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )

        assert uncertainties.shape == sigma_interp.shape
        # Uncertainties should be bounded
        assert np.all(uncertainties >= 0)
