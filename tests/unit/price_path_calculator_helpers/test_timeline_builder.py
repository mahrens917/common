"""Tests for price_path_calculator_helpers.timeline_builder module."""

import numpy as np
import pytest

from common.price_path_calculator_helpers.metrics_extractor import (
    PricePathComputationError,
)
from common.price_path_calculator_helpers.timeline_builder import TimelineBuilder

# Test constants for sigma timelines
SIGMA_TIMELINE_SHORT = (0.0, 0.01, 0.02, 0.03)
SIGMA_TIMELINE_LONG = (0.0, 1.0, 2.0, 3.0)
SIGMA_TIMELINE_VERY_SHORT = (0.0, 0.001, 0.002)


class TestTimelineBuilderInit:
    """Tests for TimelineBuilder initialization."""

    def test_stores_parameters(self) -> None:
        """Test initialization stores parameters."""
        builder = TimelineBuilder(min_horizon_days=0.5, timeline_points=100)

        assert builder._min_horizon_days == 0.5
        assert builder._timeline_points == 100


class TestTimelineBuilderGenerateTimeline:
    """Tests for _generate_timeline method."""

    def test_generates_evenly_spaced_timeline(self) -> None:
        """Test generates evenly spaced timeline."""
        builder = TimelineBuilder(min_horizon_days=0.1, timeline_points=10)

        result = builder._generate_timeline(30.0)

        assert len(result) == 10
        assert result[0] > 0
        assert result[-1] == pytest.approx(30.0)

    def test_respects_min_horizon(self) -> None:
        """Test respects minimum horizon constraint."""
        builder = TimelineBuilder(min_horizon_days=5.0, timeline_points=10)

        result = builder._generate_timeline(30.0)

        assert result[0] >= 5.0

    def test_public_wrapper_works(self) -> None:
        """Test public generate_timeline works."""
        builder = TimelineBuilder(min_horizon_days=0.1, timeline_points=10)

        result = builder.generate_timeline(30.0)

        assert len(result) == 10


class TestTimelineBuilderDerivePredictionTimeline:
    """Tests for derive_prediction_timeline method."""

    def test_constrains_to_metrics_range(self) -> None:
        """Test constrains timeline to metrics range."""
        builder = TimelineBuilder(min_horizon_days=0.1, timeline_points=100)
        sigma_timeline = np.array(SIGMA_TIMELINE_SHORT)  # Max 0.03 years

        timeline_years, timeline_days = builder.derive_prediction_timeline(
            sigma_timeline=sigma_timeline,
            prediction_horizon_days=30.0,
            currency="BTC",
            training_range=None,
        )

        # All timeline points should be <= max sigma timeline value
        assert np.all(timeline_years <= 0.03)

    def test_constrains_to_training_range(self) -> None:
        """Test constrains timeline to training range."""
        builder = TimelineBuilder(min_horizon_days=0.1, timeline_points=100)
        sigma_timeline = np.array(SIGMA_TIMELINE_LONG)  # Max 3 years
        training_range = [0.0, 0.5]  # Max 0.5 years

        timeline_years, timeline_days = builder.derive_prediction_timeline(
            sigma_timeline=sigma_timeline,
            prediction_horizon_days=30.0,
            currency="ETH",
            training_range=training_range,
        )

        assert np.all(timeline_years <= 0.5)

    def test_raises_when_horizon_exceeds_metrics(self) -> None:
        """Test raises error when horizon exceeds metrics range."""
        builder = TimelineBuilder(min_horizon_days=1.0, timeline_points=100)
        # Very short sigma timeline that ends before any predictions
        sigma_timeline = np.array(SIGMA_TIMELINE_VERY_SHORT)  # Ends at ~0.7 days

        with pytest.raises(PricePathComputationError) as exc_info:
            builder.derive_prediction_timeline(
                sigma_timeline=sigma_timeline,
                prediction_horizon_days=365.0,
                currency="BTC",
                training_range=None,
            )

        assert "precomputed range" in str(exc_info.value)
        assert "BTC" in str(exc_info.value)

    def test_raises_when_horizon_exceeds_training(self) -> None:
        """Test raises error when horizon exceeds training range."""
        builder = TimelineBuilder(min_horizon_days=1.0, timeline_points=100)
        sigma_timeline = np.array(SIGMA_TIMELINE_LONG)
        training_range = [0.0, 0.001]  # Very short training range

        with pytest.raises(PricePathComputationError) as exc_info:
            builder.derive_prediction_timeline(
                sigma_timeline=sigma_timeline,
                prediction_horizon_days=365.0,
                currency="ETH",
                training_range=training_range,
            )

        assert "training range" in str(exc_info.value)
        assert "ETH" in str(exc_info.value)

    def test_returns_matching_years_and_days(self) -> None:
        """Test returned years and days have matching lengths."""
        builder = TimelineBuilder(min_horizon_days=0.1, timeline_points=50)
        sigma_timeline = np.array(SIGMA_TIMELINE_LONG)

        timeline_years, timeline_days = builder.derive_prediction_timeline(
            sigma_timeline=sigma_timeline,
            prediction_horizon_days=30.0,
            currency="BTC",
            training_range=None,
        )

        assert len(timeline_years) == len(timeline_days)
        assert len(timeline_years) > 0
