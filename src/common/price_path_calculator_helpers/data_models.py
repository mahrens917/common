"""Data models for price path calculation."""

from dataclasses import dataclass

import numpy as np


class PricePathComputationError(Exception):
    """Raised when the most probable price path cannot be computed."""


@dataclass(frozen=True)
class PricePathPoint:
    timestamp: float
    expected_price: float
    uncertainty: float


@dataclass(frozen=True)
class PathMetrics:
    sigma_timeline: np.ndarray
    sigma_mid_mean: np.ndarray
    sigma_mid_p95: np.ndarray
    moneyness_grid: np.ndarray
    forward_curve: np.ndarray
    bid_second_grid: np.ndarray
    ask_second_grid: np.ndarray
