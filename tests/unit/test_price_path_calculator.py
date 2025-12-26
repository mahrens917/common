"""Tests for price_path_calculator module."""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from common.price_path_calculator import (
    FAILED_TO_GENERATE_METRICS_TEMPLATE,
    GP_SURFACE_MISSING_FUTURES_CURVE_TEMPLATE,
    INVALID_MONEYNESS_ERROR,
    MIN_HORIZON_DAYS_NOT_POSITIVE_ERROR,
    MIN_STRIKE_COUNT,
    MIN_TIMELINE_POINTS,
    NON_CALLABLE_ENSURE_PATH_METRICS_TEMPLATE,
    PREDICTION_HORIZON_DAYS_NOT_POSITIVE_ERROR,
    STRIKE_COUNT_TOO_SMALL_ERROR,
    TIMELINE_POINTS_TOO_SMALL_ERROR,
    MostProbablePricePathCalculator,
)
from common.price_path_calculator_helpers.config import PricePathCalculatorConfig
from common.price_path_calculator_helpers.data_models import PathMetrics
from common.price_path_calculator_helpers.dependencies_factory import (
    PricePathCalculatorDependencies,
)
from common.price_path_calculator_helpers.metrics_extractor import (
    PricePathComputationError,
)

# Test constants
TEST_STRIKE_COUNT = 64
TEST_MIN_MONEYNESS = 0.5
TEST_MAX_MONEYNESS = 1.5
TEST_TIMELINE_POINTS = 10
TEST_MIN_HORIZON_DAYS = 1.0
TEST_PREDICTION_HORIZON_DAYS = 30.0
TEST_CURRENCY = "BTC"
TEST_SIGMA_MIN_RATIO = 0.002
TEST_SIGMA_MAX_RATIO = 0.10


def _create_mock_dependencies(
    surface_loader=None,
    metrics_extractor=None,
    timeline_builder=None,
    expectation_integrator=None,
    path_interpolator=None,
    expectation_scaler=None,
):
    """Create PricePathCalculatorDependencies with mocked components."""
    return PricePathCalculatorDependencies(
        surface_loader=surface_loader or MagicMock(),
        metrics_extractor=metrics_extractor or MagicMock(),
        timeline_builder=timeline_builder or MagicMock(),
        expectation_integrator=expectation_integrator or MagicMock(),
        path_interpolator=path_interpolator or MagicMock(),
        expectation_scaler=expectation_scaler or MagicMock(),
    )


class TestMostProbablePricePathCalculatorInit:
    """Tests for MostProbablePricePathCalculator initialization."""

    def test_raises_when_strike_count_too_small(self) -> None:
        """Test raises TypeError when strike_count is below minimum."""
        config = PricePathCalculatorConfig(
            strike_count=MIN_STRIKE_COUNT - 1,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == STRIKE_COUNT_TOO_SMALL_ERROR

    def test_raises_when_min_moneyness_zero(self) -> None:
        """Test raises TypeError when min_moneyness is zero."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=0.0,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == INVALID_MONEYNESS_ERROR

    def test_raises_when_min_moneyness_negative(self) -> None:
        """Test raises TypeError when min_moneyness is negative."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=-0.5,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == INVALID_MONEYNESS_ERROR

    def test_raises_when_min_moneyness_exceeds_max(self) -> None:
        """Test raises TypeError when min_moneyness >= max_moneyness."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=2.0,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == INVALID_MONEYNESS_ERROR

    def test_raises_when_timeline_points_too_small(self) -> None:
        """Test raises TypeError when timeline_points is below minimum."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=MIN_TIMELINE_POINTS - 1,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == TIMELINE_POINTS_TOO_SMALL_ERROR

    def test_raises_when_min_horizon_days_zero(self) -> None:
        """Test raises TypeError when min_horizon_days is zero."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=0.0,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == MIN_HORIZON_DAYS_NOT_POSITIVE_ERROR

    def test_raises_when_min_horizon_days_negative(self) -> None:
        """Test raises TypeError when min_horizon_days is negative."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=-1.0,
        )

        with pytest.raises(TypeError) as exc_info:
            MostProbablePricePathCalculator(config=config)

        assert str(exc_info.value) == MIN_HORIZON_DAYS_NOT_POSITIVE_ERROR

    def test_uses_default_surface_loader_when_none(self) -> None:
        """Test uses default surface loader when config.surface_loader is None."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            surface_loader=None,
        )

        calculator = MostProbablePricePathCalculator(config=config)

        assert calculator._surface_loader_fn is not None

    def test_uses_provided_surface_loader(self) -> None:
        """Test uses provided surface loader when specified."""
        mock_loader = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            surface_loader=mock_loader,
        )

        calculator = MostProbablePricePathCalculator(config=config)

        assert calculator._surface_loader_fn is mock_loader

    def test_sets_progress_callback(self) -> None:
        """Test sets progress_callback from config."""
        mock_callback = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )

        calculator = MostProbablePricePathCalculator(config=config)

        assert calculator._progress_callback is mock_callback

    def test_uses_provided_dependencies(self) -> None:
        """Test uses provided dependencies when specified."""
        mock_surface_loader = MagicMock()
        mock_metrics_extractor = MagicMock()
        mock_timeline_builder = MagicMock()

        mock_deps = PricePathCalculatorDependencies(
            surface_loader=mock_surface_loader,
            metrics_extractor=mock_metrics_extractor,
            timeline_builder=mock_timeline_builder,
            expectation_integrator=MagicMock(),
            path_interpolator=MagicMock(),
            expectation_scaler=MagicMock(),
        )
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )

        calculator = MostProbablePricePathCalculator(config=config)

        assert calculator._surface_loader is mock_surface_loader
        assert calculator._metrics_extractor is mock_metrics_extractor
        assert calculator._timeline_builder is mock_timeline_builder

    def test_creates_default_dependencies_when_none(self) -> None:
        """Test creates default dependencies when config.dependencies is None."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )

        calculator = MostProbablePricePathCalculator(config=config)

        assert calculator._surface_loader is not None
        assert calculator._metrics_extractor is not None
        assert calculator._timeline_builder is not None


class TestMostProbablePricePathCalculatorGeneratePricePath:
    """Tests for generate_price_path method."""

    def test_raises_when_prediction_horizon_zero(self) -> None:
        """Test raises TypeError when prediction_horizon_days is zero."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        with pytest.raises(TypeError) as exc_info:
            calculator.generate_price_path(TEST_CURRENCY, prediction_horizon_days=0.0)

        assert str(exc_info.value) == PREDICTION_HORIZON_DAYS_NOT_POSITIVE_ERROR

    def test_raises_when_prediction_horizon_negative(self) -> None:
        """Test raises TypeError when prediction_horizon_days is negative."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        with pytest.raises(TypeError) as exc_info:
            calculator.generate_price_path(TEST_CURRENCY, prediction_horizon_days=-10.0)

        assert str(exc_info.value) == PREDICTION_HORIZON_DAYS_NOT_POSITIVE_ERROR

    def test_raises_when_surface_missing_futures_curve(self) -> None:
        """Test raises when surface.futures_curve is None."""
        mock_surface = MagicMock()
        mock_surface.futures_curve = None

        mock_surface_loader = MagicMock()
        mock_surface_loader.load_surface.return_value = mock_surface

        mock_deps = _create_mock_dependencies(surface_loader=mock_surface_loader)

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        with pytest.raises(PricePathComputationError) as exc_info:
            calculator.generate_price_path(TEST_CURRENCY)

        assert TEST_CURRENCY.upper() in str(exc_info.value)
        assert "futures curve" in str(exc_info.value).lower()

    def test_returns_price_path_with_timestamps_prices_uncertainties(self) -> None:
        """Test returns list of tuples with timestamps, prices, and uncertainties."""
        test_timeline_years = np.array([0.1, 0.2, 0.3])
        test_timeline_days = np.array([36.5, 73.0, 109.5])
        test_expected_prices = np.array([50000.0, 51000.0, 52000.0])
        test_uncertainties = np.array([1000.0, 1100.0, 1200.0])

        mock_surface = MagicMock()
        mock_surface.futures_curve = MagicMock()

        mock_path_metrics = MagicMock(spec=PathMetrics)
        mock_path_metrics.sigma_timeline = test_timeline_years

        mock_surface_loader = MagicMock()
        mock_surface_loader.load_surface.return_value = mock_surface

        mock_metrics_extractor = MagicMock()
        mock_metrics_extractor.extract_path_metrics.return_value = mock_path_metrics

        mock_timeline_builder = MagicMock()
        mock_timeline_builder.derive_prediction_timeline.return_value = (
            test_timeline_years,
            test_timeline_days,
        )

        mock_expectation_integrator = MagicMock()
        mock_expectation_integrator.integrate_expectation.return_value = np.array([0.1, 0.2, 0.3])

        mock_path_interpolator = MagicMock()
        mock_path_interpolator.interpolate_path_series.return_value = (
            np.array([0.01, 0.02, 0.03]),
            np.array([0.015, 0.025, 0.035]),
            np.array([0.5, 0.6, 0.7]),
            np.array([1.0, 1.0, 1.0]),
        )

        mock_expectation_scaler = MagicMock()
        mock_expectation_scaler.scale_expectations.return_value = (
            test_expected_prices,
            test_uncertainties,
        )

        mock_deps = _create_mock_dependencies(
            surface_loader=mock_surface_loader,
            metrics_extractor=mock_metrics_extractor,
            timeline_builder=mock_timeline_builder,
            expectation_integrator=mock_expectation_integrator,
            path_interpolator=mock_path_interpolator,
            expectation_scaler=mock_expectation_scaler,
        )

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        with patch("common.price_path_calculator.time.time", return_value=1000000.0):
            result = calculator.generate_price_path(TEST_CURRENCY)

        assert len(result) == 3
        assert all(isinstance(item, tuple) for item in result)
        assert all(len(item) == 3 for item in result)

    def test_calls_surface_loader_with_currency(self) -> None:
        """Test calls surface_loader.load_surface with currency."""
        test_timeline_years = np.array([0.1])
        test_timeline_days = np.array([36.5])

        mock_surface = MagicMock()
        mock_surface.futures_curve = MagicMock()

        mock_path_metrics = MagicMock(spec=PathMetrics)
        mock_path_metrics.sigma_timeline = test_timeline_years

        mock_surface_loader = MagicMock()
        mock_surface_loader.load_surface.return_value = mock_surface

        mock_metrics_extractor = MagicMock()
        mock_metrics_extractor.extract_path_metrics.return_value = mock_path_metrics

        mock_timeline_builder = MagicMock()
        mock_timeline_builder.derive_prediction_timeline.return_value = (
            test_timeline_years,
            test_timeline_days,
        )

        mock_expectation_integrator = MagicMock()
        mock_expectation_integrator.integrate_expectation.return_value = np.array([0.1])

        mock_path_interpolator = MagicMock()
        mock_path_interpolator.interpolate_path_series.return_value = (
            np.array([0.01]),
            np.array([0.015]),
            np.array([0.5]),
            np.array([1.0]),
        )

        mock_expectation_scaler = MagicMock()
        mock_expectation_scaler.scale_expectations.return_value = (
            np.array([50000.0]),
            np.array([1000.0]),
        )

        mock_deps = _create_mock_dependencies(
            surface_loader=mock_surface_loader,
            metrics_extractor=mock_metrics_extractor,
            timeline_builder=mock_timeline_builder,
            expectation_integrator=mock_expectation_integrator,
            path_interpolator=mock_path_interpolator,
            expectation_scaler=mock_expectation_scaler,
        )

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator.generate_price_path(TEST_CURRENCY)

        args = mock_surface_loader.load_surface.call_args[0]
        assert args[0] == TEST_CURRENCY

    def test_calls_emit_progress_with_timeline_length(self) -> None:
        """Test calls _emit_progress with timeline length."""
        test_timeline_years = np.array([0.1, 0.2, 0.3])
        test_timeline_days = np.array([36.5, 73.0, 109.5])

        mock_surface = MagicMock()
        mock_surface.futures_curve = MagicMock()

        mock_path_metrics = MagicMock(spec=PathMetrics)
        mock_path_metrics.sigma_timeline = test_timeline_years

        mock_callback = MagicMock()

        mock_deps = _create_mock_dependencies()
        mock_deps.surface_loader.load_surface.return_value = mock_surface
        mock_deps.metrics_extractor.extract_path_metrics.return_value = mock_path_metrics
        mock_deps.timeline_builder.derive_prediction_timeline.return_value = (
            test_timeline_years,
            test_timeline_days,
        )
        mock_deps.expectation_integrator.integrate_expectation.return_value = np.array([0.1, 0.2, 0.3])
        mock_deps.path_interpolator.interpolate_path_series.return_value = (
            np.array([0.01, 0.02, 0.03]),
            np.array([0.015, 0.025, 0.035]),
            np.array([0.5, 0.6, 0.7]),
            np.array([1.0, 1.0, 1.0]),
        )
        mock_deps.expectation_scaler.scale_expectations.return_value = (
            np.array([50000.0, 51000.0, 52000.0]),
            np.array([1000.0, 1100.0, 1200.0]),
        )

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator.generate_price_path(TEST_CURRENCY)

        mock_callback.assert_called()

    def test_uses_futures_curve_metadata_when_present(self) -> None:
        """Test uses futures_curve_metadata when available on surface."""
        test_timeline_years = np.array([0.1])
        test_timeline_days = np.array([36.5])
        test_metadata = {"training_time_range": (1000.0, 2000.0)}

        mock_surface = MagicMock()
        mock_surface.futures_curve = MagicMock()
        mock_surface.futures_curve_metadata = test_metadata

        mock_path_metrics = MagicMock(spec=PathMetrics)
        mock_path_metrics.sigma_timeline = test_timeline_years

        mock_deps = _create_mock_dependencies()
        mock_deps.surface_loader.load_surface.return_value = mock_surface
        mock_deps.metrics_extractor.extract_path_metrics.return_value = mock_path_metrics
        mock_deps.timeline_builder.derive_prediction_timeline.return_value = (
            test_timeline_years,
            test_timeline_days,
        )
        mock_deps.expectation_integrator.integrate_expectation.return_value = np.array([0.1])
        mock_deps.path_interpolator.interpolate_path_series.return_value = (
            np.array([0.01]),
            np.array([0.015]),
            np.array([0.5]),
            np.array([1.0]),
        )
        mock_deps.expectation_scaler.scale_expectations.return_value = (
            np.array([50000.0]),
            np.array([1000.0]),
        )

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator.generate_price_path(TEST_CURRENCY)

        call_kwargs = mock_deps.timeline_builder.derive_prediction_timeline.call_args[1]
        assert call_kwargs["training_range"] == (1000.0, 2000.0)

    def test_uses_none_training_range_when_metadata_missing(self) -> None:
        """Test uses None for training_range when metadata is missing."""
        test_timeline_years = np.array([0.1])
        test_timeline_days = np.array([36.5])

        mock_surface = MagicMock()
        mock_surface.futures_curve = MagicMock()
        del mock_surface.futures_curve_metadata

        mock_path_metrics = MagicMock(spec=PathMetrics)
        mock_path_metrics.sigma_timeline = test_timeline_years

        mock_deps = _create_mock_dependencies()
        mock_deps.surface_loader.load_surface.return_value = mock_surface
        mock_deps.metrics_extractor.extract_path_metrics.return_value = mock_path_metrics
        mock_deps.timeline_builder.derive_prediction_timeline.return_value = (
            test_timeline_years,
            test_timeline_days,
        )
        mock_deps.expectation_integrator.integrate_expectation.return_value = np.array([0.1])
        mock_deps.path_interpolator.interpolate_path_series.return_value = (
            np.array([0.01]),
            np.array([0.015]),
            np.array([0.5]),
            np.array([1.0]),
        )
        mock_deps.expectation_scaler.scale_expectations.return_value = (
            np.array([50000.0]),
            np.array([1000.0]),
        )

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator.generate_price_path(TEST_CURRENCY)

        call_kwargs = mock_deps.timeline_builder.derive_prediction_timeline.call_args[1]
        assert call_kwargs["training_range"] is None


class TestEnsurePathMetrics:
    """Tests for _ensure_path_metrics static method."""

    def test_does_nothing_when_ensure_path_metrics_missing(self) -> None:
        """Test completes successfully when surface has no ensure_path_metrics."""
        mock_surface = MagicMock()
        del mock_surface.ensure_path_metrics

        MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

    def test_calls_ensure_path_metrics_when_callable(self) -> None:
        """Test calls ensure_path_metrics when it is callable."""
        mock_ensure = MagicMock()
        mock_surface = MagicMock()
        mock_surface.ensure_path_metrics = mock_ensure

        MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

        mock_ensure.assert_called_once()

    def test_raises_when_ensure_path_metrics_not_callable(self) -> None:
        """Test raises when ensure_path_metrics exists but is not callable."""
        mock_surface = MagicMock()
        mock_surface.ensure_path_metrics = "not_callable"

        with pytest.raises(PricePathComputationError) as exc_info:
            MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

        assert TEST_CURRENCY.upper() in str(exc_info.value)
        assert "non-callable" in str(exc_info.value).lower()

    def test_raises_when_ensure_path_metrics_raises_value_error(self) -> None:
        """Test raises PricePathComputationError when ensure_path_metrics raises ValueError."""
        mock_ensure = MagicMock(side_effect=ValueError("test error"))
        mock_surface = MagicMock()
        mock_surface.ensure_path_metrics = mock_ensure

        with pytest.raises(PricePathComputationError) as exc_info:
            MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

        assert TEST_CURRENCY.upper() in str(exc_info.value)

    def test_raises_when_ensure_path_metrics_raises_runtime_error(self) -> None:
        """Test raises PricePathComputationError when ensure_path_metrics raises RuntimeError."""
        mock_ensure = MagicMock(side_effect=RuntimeError("test error"))
        mock_surface = MagicMock()
        mock_surface.ensure_path_metrics = mock_ensure

        with pytest.raises(PricePathComputationError) as exc_info:
            MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

        assert TEST_CURRENCY.upper() in str(exc_info.value)

    def test_raises_when_ensure_path_metrics_raises_os_error(self) -> None:
        """Test raises PricePathComputationError when ensure_path_metrics raises OSError."""
        mock_ensure = MagicMock(side_effect=OSError("test error"))
        mock_surface = MagicMock()
        mock_surface.ensure_path_metrics = mock_ensure

        with pytest.raises(PricePathComputationError) as exc_info:
            MostProbablePricePathCalculator._ensure_path_metrics(mock_surface, TEST_CURRENCY)

        assert TEST_CURRENCY.upper() in str(exc_info.value)


class TestBuildTimestamps:
    """Tests for _build_timestamps static method."""

    def test_converts_days_to_timestamps(self) -> None:
        """Test converts timeline_days to future timestamps."""
        timeline_days = np.array([1.0, 2.0, 3.0])

        with patch("common.price_path_calculator.time.time", return_value=1000000.0):
            result = MostProbablePricePathCalculator._build_timestamps(timeline_days)

        expected = 1000000.0 + timeline_days * 24.0 * 3600.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_handles_zero_days(self) -> None:
        """Test handles zero days correctly."""
        timeline_days = np.array([0.0])

        with patch("common.price_path_calculator.time.time", return_value=5000000.0):
            result = MostProbablePricePathCalculator._build_timestamps(timeline_days)

        assert result[0] == 5000000.0


class TestEmitProgress:
    """Tests for _emit_progress method."""

    def test_does_nothing_when_callback_none(self) -> None:
        """Test does nothing when progress_callback is None."""
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=None,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(10)

    def test_does_nothing_when_total_steps_zero(self) -> None:
        """Test does nothing when total_steps is zero."""
        mock_callback = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(0)

        mock_callback.assert_not_called()

    def test_does_nothing_when_total_steps_negative(self) -> None:
        """Test does nothing when total_steps is negative."""
        mock_callback = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(-5)

        mock_callback.assert_not_called()

    def test_calls_callback_at_intervals(self) -> None:
        """Test calls callback at regular intervals."""
        mock_callback = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(10)

        assert mock_callback.call_count > 0

    def test_calls_callback_with_final_step(self) -> None:
        """Test calls callback with final step."""
        mock_callback = MagicMock()
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(10)

        final_call = mock_callback.call_args_list[-1]
        assert final_call[0] == (10, 10)

    def test_stops_on_runtime_error(self) -> None:
        """Test stops calling callback after RuntimeError."""
        mock_callback = MagicMock(side_effect=RuntimeError("test error"))
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(100)

        assert mock_callback.call_count == 1

    def test_stops_on_value_error(self) -> None:
        """Test stops calling callback after ValueError."""
        mock_callback = MagicMock(side_effect=ValueError("test error"))
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(100)

        assert mock_callback.call_count == 1

    def test_stops_on_type_error(self) -> None:
        """Test stops calling callback after TypeError."""
        mock_callback = MagicMock(side_effect=TypeError("test error"))
        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            progress_callback=mock_callback,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        calculator._emit_progress(100)

        assert mock_callback.call_count == 1


class TestDefaultSurfaceLoader:
    """Tests for _default_surface_loader function."""

    def test_raises_import_error_when_pdf_not_available(self) -> None:
        """Test raises ImportError when pdf package is not available."""
        from common.price_path_calculator import _default_surface_loader

        with patch("importlib.import_module", side_effect=ImportError):
            with pytest.raises(ImportError) as exc_info:
                _default_surface_loader(TEST_CURRENCY)

            assert "pdf package not found" in str(exc_info.value)

    def test_tries_src_pdf_path_first(self) -> None:
        """Test tries src.pdf.utils.gp_surface_store first."""
        from common.price_path_calculator import _default_surface_loader

        mock_module = MagicMock()
        mock_module.load_surface_sync.return_value = MagicMock()

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            _default_surface_loader(TEST_CURRENCY)

            first_call = mock_import.call_args_list[0]
            assert first_call[0][0] == "src.pdf.utils.gp_surface_store"

    def test_tries_pdf_path_second(self) -> None:
        """Test tries pdf.utils.gp_surface_store if first fails."""
        from common.price_path_calculator import _default_surface_loader

        mock_module = MagicMock()
        mock_module.load_surface_sync.return_value = MagicMock()

        def import_side_effect(module_path):
            if module_path == "src.pdf.utils.gp_surface_store":
                raise ImportError
            return mock_module

        with patch("importlib.import_module", side_effect=import_side_effect):
            _default_surface_loader(TEST_CURRENCY)

            mock_module.load_surface_sync.assert_called_once_with(TEST_CURRENCY)

    def test_calls_load_surface_sync_with_currency(self) -> None:
        """Test calls load_surface_sync with currency parameter."""
        from common.price_path_calculator import _default_surface_loader

        mock_module = MagicMock()
        mock_surface = MagicMock()
        mock_module.load_surface_sync.return_value = mock_surface

        with patch("importlib.import_module", return_value=mock_module):
            result = _default_surface_loader(TEST_CURRENCY)

            mock_module.load_surface_sync.assert_called_once_with(TEST_CURRENCY)
            assert result is mock_surface


class TestGeneratePredictionTimeline:
    """Tests for _generate_prediction_timeline method."""

    def test_delegates_to_timeline_builder(self) -> None:
        """Test delegates to timeline_builder.generate_timeline."""
        test_horizon_days = 60.0

        mock_deps = _create_mock_dependencies()
        mock_deps.timeline_builder.generate_timeline.return_value = np.array([1.0, 2.0, 3.0])

        config = PricePathCalculatorConfig(
            strike_count=TEST_STRIKE_COUNT,
            min_moneyness=TEST_MIN_MONEYNESS,
            max_moneyness=TEST_MAX_MONEYNESS,
            timeline_points=TEST_TIMELINE_POINTS,
            min_horizon_days=TEST_MIN_HORIZON_DAYS,
            dependencies=mock_deps,
        )
        calculator = MostProbablePricePathCalculator(config=config)

        result = calculator._generate_prediction_timeline(test_horizon_days)

        mock_deps.timeline_builder.generate_timeline.assert_called_once_with(test_horizon_days)
        assert result is mock_deps.timeline_builder.generate_timeline.return_value
