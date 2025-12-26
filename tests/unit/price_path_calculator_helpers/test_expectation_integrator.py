"""Tests for price_path_calculator_helpers.expectation_integrator module."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from common.price_path_calculator_helpers.expectation_integrator import (
    MIN_DENSITY_INTEGRAL_THRESHOLD,
    ExpectationIntegrator,
    PricePathComputationError,
)

# Test constants
TEST_FORWARD_CURVE = (100.0, 101.0, 102.0)
TEST_MONEYNESS_GRID = (0.9, 1.0, 1.1)
TEST_FORWARD_CURVE_WITH_NEGATIVE = (100.0, -1.0, 102.0)
TEST_FORWARD_CURVE_WITH_ZERO = (100.0, 0.0, 102.0)
TEST_GRID_ROW_WITH_INF = (np.inf, 1.0, 1.0)


class TestExpectationIntegratorConstants:
    """Tests for module constants."""

    def test_min_density_threshold(self) -> None:
        """Test minimum density threshold."""
        assert MIN_DENSITY_INTEGRAL_THRESHOLD == 1e-8


class TestExpectationIntegratorIntegrateExpectation:
    """Tests for integrate_expectation method."""

    def test_integrates_valid_metrics(self) -> None:
        """Test integrates valid metrics."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        mock_metrics.bid_second_grid = np.ones((3, 3)) * 0.5
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 0.5

        result = integrator.integrate_expectation(mock_metrics)

        assert result.shape == (3,)
        assert np.all(np.isfinite(result))

    def test_raises_on_non_positive_strikes(self) -> None:
        """Test raises error on non-positive strikes."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE_WITH_NEGATIVE)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        mock_metrics.bid_second_grid = np.ones((3, 3)) * 0.5
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 0.5

        with pytest.raises(PricePathComputationError) as exc_info:
            integrator.integrate_expectation(mock_metrics)

        assert "Non-positive strikes" in str(exc_info.value)

    def test_raises_on_zero_strike(self) -> None:
        """Test raises error on zero strikes."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE_WITH_ZERO)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        mock_metrics.bid_second_grid = np.ones((3, 3)) * 0.5
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 0.5

        with pytest.raises(PricePathComputationError) as exc_info:
            integrator.integrate_expectation(mock_metrics)

        assert "Non-positive strikes" in str(exc_info.value)

    def test_raises_on_non_finite_result(self) -> None:
        """Test raises error on non-finite integration result."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        # Create grids that would produce inf/nan
        mock_metrics.bid_second_grid = np.array([TEST_GRID_ROW_WITH_INF] * 3)
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 0.5

        with pytest.raises(PricePathComputationError) as exc_info:
            integrator.integrate_expectation(mock_metrics)

        assert "Non-finite values" in str(exc_info.value)

    def test_uses_forward_curve_for_low_density(self) -> None:
        """Test uses forward curve when density integral is below threshold."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        # Very small density values
        mock_metrics.bid_second_grid = np.ones((3, 3)) * 1e-12
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 1e-12

        result = integrator.integrate_expectation(mock_metrics)

        # Should fall back to forward curve
        np.testing.assert_array_almost_equal(result, mock_metrics.forward_curve)

    def test_handles_positive_results(self) -> None:
        """Test returns positive results."""
        integrator = ExpectationIntegrator()
        mock_metrics = MagicMock()
        mock_metrics.forward_curve = np.array(TEST_FORWARD_CURVE)
        mock_metrics.moneyness_grid = np.array(TEST_MONEYNESS_GRID)
        mock_metrics.bid_second_grid = np.ones((3, 3)) * 0.3
        mock_metrics.ask_second_grid = np.ones((3, 3)) * 0.7

        result = integrator.integrate_expectation(mock_metrics)

        assert np.all(result > 0)
