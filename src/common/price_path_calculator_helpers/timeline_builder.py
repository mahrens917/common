"""Build prediction timelines."""

from typing import Optional, Sequence, Tuple

import numpy as np

from .metrics_extractor import PricePathComputationError


class TimelineBuilder:
    """Build and validate prediction timelines."""

    def __init__(self, min_horizon_days: float, timeline_points: int):
        self._min_horizon_days = min_horizon_days
        self._timeline_points = timeline_points

    def derive_prediction_timeline(
        self,
        *,
        sigma_timeline: np.ndarray,
        prediction_horizon_days: float,
        currency: str,
        training_range: Optional[Sequence[float]],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Derive timeline constrained by precomputed metrics and training range."""
        timeline_days = self._generate_timeline(prediction_horizon_days)
        timeline_years = timeline_days / 365.25

        # Constrain to metrics range
        max_tau_metrics = float(sigma_timeline[-1])
        timeline_mask = timeline_years <= max_tau_metrics
        if not np.any(timeline_mask):
            raise PricePathComputationError(
                f"Prediction horizon exceeds precomputed range for {currency.upper()}"
            )
        timeline_years = timeline_years[timeline_mask]
        timeline_days = timeline_days[timeline_mask]

        # Constrain to training range
        if training_range is not None:
            max_tau_training = float(training_range[1])
            training_mask = timeline_years <= max_tau_training
            if not np.any(training_mask):
                raise PricePathComputationError(
                    f"Prediction horizon exceeds futures training range for {currency.upper()}"
                )
            timeline_years = timeline_years[training_mask]
            timeline_days = timeline_days[training_mask]

        if timeline_years.size == 0:
            raise PricePathComputationError("Prediction timeline generation produced no points")

        return timeline_years, timeline_days

    def _generate_timeline(self, horizon_days: float) -> np.ndarray:
        """Generate evenly-spaced timeline."""
        start = max(self._min_horizon_days, horizon_days / (self._timeline_points * 2.0))
        timeline = np.linspace(start, float(horizon_days), self._timeline_points)
        return timeline.astype(np.float64, copy=False)

    def generate_timeline(self, horizon_days: float) -> np.ndarray:
        """Public wrapper for timeline generation."""
        return self._generate_timeline(horizon_days)
