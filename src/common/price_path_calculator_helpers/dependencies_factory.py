from __future__ import annotations

"""Dependency factory for MostProbablePricePathCalculator."""


from dataclasses import dataclass

from . import (
    ExpectationIntegrator,
    ExpectationScaler,
    MetricsExtractor,
    PathInterpolator,
    SurfaceLoader,
    TimelineBuilder,
)


@dataclass
class PricePathCalculatorDependencies:
    """Container for all MostProbablePricePathCalculator dependencies."""

    surface_loader: SurfaceLoader
    metrics_extractor: MetricsExtractor
    timeline_builder: TimelineBuilder
    expectation_integrator: ExpectationIntegrator
    path_interpolator: PathInterpolator
    expectation_scaler: ExpectationScaler


class PricePathCalculatorDependenciesFactory:
    """Factory for creating MostProbablePricePathCalculator dependencies."""

    @staticmethod
    def create(
        min_horizon_days: float,
        timeline_points: int,
        sigma_min_ratio: float,
        sigma_max_ratio: float,
    ) -> PricePathCalculatorDependencies:
        """Create all dependencies for MostProbablePricePathCalculator."""
        surface_loader = SurfaceLoader()
        metrics_extractor = MetricsExtractor()
        timeline_builder = TimelineBuilder(min_horizon_days, timeline_points)
        expectation_integrator = ExpectationIntegrator()
        path_interpolator = PathInterpolator()
        expectation_scaler = ExpectationScaler(
            sigma_min_ratio=sigma_min_ratio, sigma_max_ratio=sigma_max_ratio
        )

        return PricePathCalculatorDependencies(
            surface_loader=surface_loader,
            metrics_extractor=metrics_extractor,
            timeline_builder=timeline_builder,
            expectation_integrator=expectation_integrator,
            path_interpolator=path_interpolator,
            expectation_scaler=expectation_scaler,
        )
