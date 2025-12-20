"""Integrate probability densities to compute expectations."""

import numpy as np

from .metrics_extractor import PathMetrics

# Integration thresholds
MIN_DENSITY_INTEGRAL_THRESHOLD = 1e-8


class PricePathComputationError(Exception):
    """Raised when price path computation fails."""


class ExpectationIntegrator:
    """Integrate density grids to compute expected prices."""

    def integrate_expectation(self, metrics: PathMetrics) -> np.ndarray:
        """Integrate probability density to compute normalized expectations."""
        strikes_grid = metrics.forward_curve[:, None] * metrics.moneyness_grid[None, :]
        if not np.all(strikes_grid > 0.0):
            raise PricePathComputationError("Non-positive strikes encountered during integration")

        mid_second_grid = 0.5 * (metrics.bid_second_grid + metrics.ask_second_grid)
        integrand = strikes_grid * mid_second_grid
        density_integral = np.asarray(
            np.trapezoid(mid_second_grid, x=strikes_grid, axis=1), dtype=float
        )
        expected_curve = np.asarray(np.trapezoid(integrand, x=strikes_grid, axis=1), dtype=float)

        if not (np.all(np.isfinite(expected_curve)) and np.all(np.isfinite(density_integral))):
            raise PricePathComputationError(
                "Non-finite values produced during expectation integration"
            )

        with np.errstate(divide="ignore", invalid="ignore"):
            normalized_expectation = np.where(
                density_integral > MIN_DENSITY_INTEGRAL_THRESHOLD,
                expected_curve / density_integral,
                metrics.forward_curve,
            )

        normalized_expectation = np.where(
            np.isfinite(normalized_expectation) & (normalized_expectation > 0.0),
            normalized_expectation,
            metrics.forward_curve,
        )

        return normalized_expectation
