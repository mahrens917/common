"""Scale expectations and uncertainties to spot price."""

from __future__ import annotations

from typing import Any, Tuple

import numpy as np


class ExpectationScaler:
    """Scale theoretical expectations to current spot price."""

    def __init__(self, *, sigma_min_ratio: float, sigma_max_ratio: float):
        self._sigma_min_ratio = sigma_min_ratio
        self._sigma_max_ratio = sigma_max_ratio

    def scale_expectations(
        self,
        *,
        surface: Any,
        expected_interp: np.ndarray,
        forward_interp: np.ndarray,
        sigma_interp: np.ndarray,
        sigma_p95_interp: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Scale expectations to spot price and compute bounded uncertainties."""
        if surface.spot_price and surface.spot_price > 0.0:
            spot_reference = float(surface.spot_price)
        elif expected_interp.size:
            spot_reference = float(expected_interp[0])
        else:
            spot_reference = float(forward_interp[0])

        if expected_interp.size:
            reference_expectation = float(expected_interp[0])
        else:
            reference_expectation = spot_reference
        if reference_expectation <= 0.0:
            reference_expectation = float(forward_interp[0])

        if reference_expectation:
            scale_ratio = spot_reference / reference_expectation
        else:
            scale_ratio = 1.0

        expected_prices = expected_interp * scale_ratio
        scaled_sigma = np.abs(scale_ratio) * sigma_interp

        min_sigma = np.maximum(expected_prices * self._sigma_min_ratio, scaled_sigma * 0.5)
        max_sigma = np.maximum(expected_prices * self._sigma_max_ratio, np.abs(scale_ratio) * sigma_p95_interp)
        uncertainties = np.clip(scaled_sigma, min_sigma, max_sigma)

        return expected_prices, uncertainties
