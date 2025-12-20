"""Scale expectations and uncertainties to spot price."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

import numpy as np

if TYPE_CHECKING:
    from src.pdf.phases.phase_5_gp_interpolation import MicroPriceGPSurface


class ExpectationScaler:
    """Scale theoretical expectations to current spot price."""

    def __init__(self, *, sigma_min_ratio: float, sigma_max_ratio: float):
        self._sigma_min_ratio = sigma_min_ratio
        self._sigma_max_ratio = sigma_max_ratio

    def scale_expectations(
        self,
        *,
        surface: MicroPriceGPSurface,
        expected_interp: np.ndarray,
        forward_interp: np.ndarray,
        sigma_interp: np.ndarray,
        sigma_p95_interp: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Scale expectations to spot price and compute bounded uncertainties."""
        if surface.spot_price and surface.spot_price > 0.0:
            spot_reference = float(surface.spot_price)
        else:
            spot_reference = float(
                expected_interp[0] if expected_interp.size else forward_interp[0]
            )

        reference_expectation = (
            float(expected_interp[0]) if expected_interp.size else spot_reference
        )
        if reference_expectation <= 0.0:
            reference_expectation = float(forward_interp[0])

        scale_ratio = spot_reference / reference_expectation if reference_expectation else 1.0

        expected_prices = expected_interp * scale_ratio
        scaled_sigma = np.abs(scale_ratio) * sigma_interp

        min_sigma = np.maximum(expected_prices * self._sigma_min_ratio, scaled_sigma * 0.5)
        max_sigma = np.maximum(
            expected_prices * self._sigma_max_ratio, np.abs(scale_ratio) * sigma_p95_interp
        )
        uncertainties = np.clip(scaled_sigma, min_sigma, max_sigma)

        return expected_prices, uncertainties
