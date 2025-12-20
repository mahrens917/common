"""Interpolate path metrics over prediction timeline."""

from typing import Tuple

import numpy as np

from .metrics_extractor import PathMetrics


class PathInterpolator:
    """Interpolate metrics along prediction timeline."""

    def interpolate_path_series(
        self,
        *,
        timeline_years: np.ndarray,
        metrics: PathMetrics,
        normalized_expectation: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Interpolate all path series to prediction timeline."""
        sigma_interp = np.interp(
            timeline_years,
            metrics.sigma_timeline,
            metrics.sigma_mid_mean,
            left=metrics.sigma_mid_mean[0],
            right=metrics.sigma_mid_mean[-1],
        )

        if metrics.sigma_mid_p95.size == metrics.sigma_timeline.size:
            sigma_p95_interp = np.interp(
                timeline_years,
                metrics.sigma_timeline,
                metrics.sigma_mid_p95,
                left=metrics.sigma_mid_p95[0],
                right=metrics.sigma_mid_p95[-1],
            )
        else:
            sigma_p95_interp = sigma_interp * 1.5

        expected_interp = np.interp(
            timeline_years,
            metrics.sigma_timeline,
            normalized_expectation,
            left=normalized_expectation[0],
            right=normalized_expectation[-1],
        )

        forward_interp = np.interp(
            timeline_years,
            metrics.sigma_timeline,
            metrics.forward_curve,
            left=metrics.forward_curve[0],
            right=metrics.forward_curve[-1],
        )

        return sigma_interp, sigma_p95_interp, expected_interp, forward_interp
