"""Extract path metrics from GP surfaces."""

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from src.pdf.phases.phase_5_gp_interpolation import MicroPriceGPSurface


class PricePathComputationError(Exception):
    """Raised when price path computation fails."""


@dataclass(frozen=True)
class PathMetrics:
    """Container for extracted path metrics."""

    sigma_timeline: np.ndarray
    sigma_mid_mean: np.ndarray
    sigma_mid_p95: np.ndarray
    moneyness_grid: np.ndarray
    forward_curve: np.ndarray
    bid_second_grid: np.ndarray
    ask_second_grid: np.ndarray


class MetricsExtractor:
    """Extract and validate path metrics from GP surfaces."""

    def extract_path_metrics(self, surface: MicroPriceGPSurface, currency: str) -> PathMetrics:
        """Extract all required path metrics from surface."""
        metrics = getattr(surface, "precomputed_path_metrics", None)
        if not metrics:
            raise PricePathComputationError(
                "GP surface missing precomputed path metrics. Rerun PDF pipeline."
            )

        sigma_timeline = self._require_metric_array(
            metrics, "timeline_years", "Missing sigma timeline"
        )
        sigma_mid_mean = self._require_metric_array(
            metrics, "mid_sigma_mean", "Missing sigma metadata"
        )
        sigma_mid_p95 = self._require_metric_array(
            metrics, "mid_sigma_p95", "Missing sigma percentiles"
        )

        if sigma_mid_mean.size == 0:
            raise PricePathComputationError("Empty sigma metadata")

        moneyness_grid = self._require_metric_array(
            metrics, "moneyness_grid", "Missing moneyness grid"
        )
        forward_curve = self._require_metric_array(
            metrics, "forward_curve", "Missing forward curve"
        )
        bid_second_grid = self._require_metric_array(
            metrics, "bid_second", "Missing bid derivative grid"
        )
        ask_second_grid = self._require_metric_array(
            metrics, "ask_second", "Missing ask derivative grid"
        )

        if (
            forward_curve.size != bid_second_grid.shape[0]
            or bid_second_grid.shape != ask_second_grid.shape
        ):
            raise PricePathComputationError("Derivative grid dimensions inconsistent")

        return PathMetrics(
            sigma_timeline=sigma_timeline,
            sigma_mid_mean=sigma_mid_mean,
            sigma_mid_p95=sigma_mid_p95,
            moneyness_grid=moneyness_grid,
            forward_curve=forward_curve,
            bid_second_grid=bid_second_grid,
            ask_second_grid=ask_second_grid,
        )

    @staticmethod
    def _require_metric_array(
        metrics: Mapping[str, Any], key: str, error_message: str
    ) -> np.ndarray:
        """Extract required metric array with validation."""
        if key not in metrics:
            raise PricePathComputationError(error_message)
        array = np.asarray(metrics[key], dtype=float)
        if array.size == 0:
            raise PricePathComputationError(error_message)
        return array
