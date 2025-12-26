"""Tests for data_models module."""

import numpy as np

from common.price_path_calculator_helpers.data_models import (
    PathMetrics,
    PricePathComputationError,
    PricePathPoint,
)


class TestPricePathComputationError:
    """Tests for PricePathComputationError exception."""

    def test_error_is_exception(self) -> None:
        """Test that PricePathComputationError is an Exception."""
        error = PricePathComputationError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self) -> None:
        """Test error message is preserved."""
        error = PricePathComputationError("custom message")
        assert str(error) == "custom message"


class TestPricePathPoint:
    """Tests for PricePathPoint dataclass."""

    def test_creation(self) -> None:
        """Test creating a PricePathPoint."""
        point = PricePathPoint(timestamp=1.5, expected_price=50000.0, uncertainty=0.05)
        assert point.timestamp == 1.5
        assert point.expected_price == 50000.0
        assert point.uncertainty == 0.05

    def test_frozen(self) -> None:
        """Test that PricePathPoint is frozen (immutable)."""
        point = PricePathPoint(timestamp=1.0, expected_price=100.0, uncertainty=0.1)
        try:
            point.timestamp = 2.0
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_equality(self) -> None:
        """Test equality comparison."""
        point1 = PricePathPoint(timestamp=1.0, expected_price=100.0, uncertainty=0.1)
        point2 = PricePathPoint(timestamp=1.0, expected_price=100.0, uncertainty=0.1)
        assert point1 == point2


class TestPathMetrics:
    """Tests for PathMetrics dataclass."""

    def test_creation(self) -> None:
        """Test creating a PathMetrics instance."""
        metrics = PathMetrics(
            sigma_timeline=np.array([0.1, 0.2]),
            sigma_mid_mean=np.array([0.15]),
            sigma_mid_p95=np.array([0.25]),
            moneyness_grid=np.array([0.9, 1.0, 1.1]),
            forward_curve=np.array([100.0, 101.0]),
            bid_second_grid=np.array([[0.01]]),
            ask_second_grid=np.array([[0.02]]),
        )
        assert len(metrics.sigma_timeline) == 2
        assert len(metrics.moneyness_grid) == 3

    def test_frozen(self) -> None:
        """Test that PathMetrics is frozen (immutable)."""
        metrics = PathMetrics(
            sigma_timeline=np.array([0.1]),
            sigma_mid_mean=np.array([0.15]),
            sigma_mid_p95=np.array([0.25]),
            moneyness_grid=np.array([1.0]),
            forward_curve=np.array([100.0]),
            bid_second_grid=np.array([[0.01]]),
            ask_second_grid=np.array([[0.02]]),
        )
        try:
            metrics.sigma_timeline = np.array([0.5])
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
