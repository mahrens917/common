from __future__ import annotations

import time
from typing import List, Tuple

from .price_path_calculator_helpers.config import PricePathCalculatorConfig
from .price_path_calculator_helpers.dependencies_factory import (
    PricePathCalculatorDependenciesFactory,
)
from .price_path_calculator_helpers.metrics_extractor import PricePathComputationError


def _default_surface_loader(currency: str):
    """Lazy-load surface loader to avoid pdf dependency at import time."""
    from src.pdf.utils.gp_surface_store import load_surface_sync

    return load_surface_sync(currency)


# Validation thresholds
MIN_STRIKE_COUNT = 32
MIN_TIMELINE_POINTS = 4

# Error messages
STRIKE_COUNT_TOO_SMALL_ERROR = "strike_count must be at least 32"
INVALID_MONEYNESS_ERROR = "min_moneyness must be positive and less than max_moneyness"
TIMELINE_POINTS_TOO_SMALL_ERROR = "timeline_points must be at least 4"
MIN_HORIZON_DAYS_NOT_POSITIVE_ERROR = "min_horizon_days must be positive"
PREDICTION_HORIZON_DAYS_NOT_POSITIVE_ERROR = "prediction_horizon_days must be positive"
GP_SURFACE_MISSING_FUTURES_CURVE_TEMPLATE = "GP surface for {} missing futures curve"
NON_CALLABLE_ENSURE_PATH_METRICS_TEMPLATE = "GP surface for {} has non-callable ensure_path_metrics"
FAILED_TO_GENERATE_METRICS_TEMPLATE = "Failed to generate metrics for {}"


class MostProbablePricePathCalculator:
    _SIGMA_MIN_RATIO, _SIGMA_MAX_RATIO = 0.002, 0.10

    def __init__(self, *, config: PricePathCalculatorConfig):

        if config.strike_count < MIN_STRIKE_COUNT:
            raise TypeError(STRIKE_COUNT_TOO_SMALL_ERROR)
        if not 0.0 < config.min_moneyness < config.max_moneyness:
            raise TypeError(INVALID_MONEYNESS_ERROR)
        if config.timeline_points < MIN_TIMELINE_POINTS:
            raise TypeError(TIMELINE_POINTS_TOO_SMALL_ERROR)
        if config.min_horizon_days <= 0.0:
            raise TypeError(MIN_HORIZON_DAYS_NOT_POSITIVE_ERROR)
        self._strike_count, self._min_moneyness = config.strike_count, config.min_moneyness
        self._max_moneyness, self._timeline_points = config.max_moneyness, config.timeline_points
        self._min_horizon_days = config.min_horizon_days
        self._surface_loader_fn = config.surface_loader or _default_surface_loader
        self._progress_callback = config.progress_callback
        deps = config.dependencies or PricePathCalculatorDependenciesFactory.create(
            config.min_horizon_days,
            config.timeline_points,
            self._SIGMA_MIN_RATIO,
            self._SIGMA_MAX_RATIO,
        )
        self._surface_loader = deps.surface_loader
        self._metrics_extractor = deps.metrics_extractor
        self._timeline_builder = deps.timeline_builder
        self._expectation_integrator = deps.expectation_integrator
        self._path_interpolator = deps.path_interpolator
        self._expectation_scaler = deps.expectation_scaler

    def generate_price_path(self, currency: str, prediction_horizon_days: float = 30.0) -> List[Tuple[float, float, float]]:
        if prediction_horizon_days <= 0:
            raise TypeError(PREDICTION_HORIZON_DAYS_NOT_POSITIVE_ERROR)
        surface = self._surface_loader.load_surface(currency, self._surface_loader_fn, self._ensure_path_metrics)
        if surface.futures_curve is None:
            raise PricePathComputationError(GP_SURFACE_MISSING_FUTURES_CURVE_TEMPLATE.format(currency.upper()))
        path_metrics = self._metrics_extractor.extract_path_metrics(surface=surface, currency=currency)
        metadata = getattr(surface, "futures_curve_metadata", None)
        training_range = metadata.get("training_time_range") if metadata else None
        timeline_years, timeline_days = self._timeline_builder.derive_prediction_timeline(
            sigma_timeline=path_metrics.sigma_timeline,
            prediction_horizon_days=prediction_horizon_days,
            currency=currency,
            training_range=training_range,
        )
        normalized_expectation = self._expectation_integrator.integrate_expectation(path_metrics)
        (
            sigma_interp,
            sigma_p95_interp,
            expected_interp,
            forward_interp,
        ) = self._path_interpolator.interpolate_path_series(
            timeline_years=timeline_years,
            metrics=path_metrics,
            normalized_expectation=normalized_expectation,
        )
        expected_prices, uncertainties = self._expectation_scaler.scale_expectations(
            surface=surface,
            expected_interp=expected_interp,
            forward_interp=forward_interp,
            sigma_interp=sigma_interp,
            sigma_p95_interp=sigma_p95_interp,
        )
        timestamps = self._build_timestamps(timeline_days)
        self._emit_progress(len(timeline_years))
        return list(zip(timestamps.tolist(), expected_prices.tolist(), uncertainties.tolist()))

    @staticmethod
    def _ensure_path_metrics(surface, currency):
        from collections.abc import Callable as CallableType

        ensure_metrics = getattr(surface, "ensure_path_metrics", None)
        if ensure_metrics and not isinstance(ensure_metrics, CallableType):
            raise PricePathComputationError(NON_CALLABLE_ENSURE_PATH_METRICS_TEMPLATE.format(currency.upper()))
        if ensure_metrics and isinstance(ensure_metrics, CallableType):
            try:
                ensure_metrics()
            except (
                ValueError,
                RuntimeError,
                OSError,
                Exception,
            ) as e:  # pragma: no cover - best-effort logging upstream
                raise PricePathComputationError(FAILED_TO_GENERATE_METRICS_TEMPLATE.format(currency.upper())) from e

    @staticmethod
    def _build_timestamps(timeline_days):
        return time.time() + timeline_days * 24.0 * 3600.0

    def _emit_progress(self, total_steps):
        if not self._progress_callback or total_steps <= 0:
            return
        interval = max(1, total_steps // 10)
        for index in range(1, total_steps + 1):
            if index % interval == 0 or index == total_steps:
                try:
                    self._progress_callback(index, total_steps)
                except (RuntimeError, ValueError, TypeError, Exception):
                    break

    def _generate_prediction_timeline(self, horizon_days: float):
        return self._timeline_builder.generate_timeline(horizon_days)
