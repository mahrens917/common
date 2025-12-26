"""Tests for data_models module."""

import numpy as np

from common.price_path_calculator_helpers.data_models import (
    PathMetrics,
    PricePathComputationError,
    PricePathPoint,
)

# Test constants for PathMetrics
TEST_SIGMA_TIMELINE_TWO = (0.1, 0.2)
TEST_SIGMA_TIMELINE_ONE = (0.1,)
TEST_SIGMA_MID_MEAN = (0.15,)
TEST_SIGMA_MID_P95 = (0.25,)
TEST_MONEYNESS_GRID_THREE = (0.9, 1.0, 1.1)
TEST_MONEYNESS_GRID_ONE = (1.0,)
TEST_FORWARD_CURVE_TWO = (100.0, 101.0)
TEST_FORWARD_CURVE_ONE = (100.0,)
TEST_BID_SECOND_GRID = ((0.01,),)
TEST_ASK_SECOND_GRID = ((0.02,),)
TEST_SIGMA_TIMELINE_MODIFIED = (0.5,)


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
            sigma_timeline=np.array(TEST_SIGMA_TIMELINE_TWO),
            sigma_mid_mean=np.array(TEST_SIGMA_MID_MEAN),
            sigma_mid_p95=np.array(TEST_SIGMA_MID_P95),
            moneyness_grid=np.array(TEST_MONEYNESS_GRID_THREE),
            forward_curve=np.array(TEST_FORWARD_CURVE_TWO),
            bid_second_grid=np.array(TEST_BID_SECOND_GRID),
            ask_second_grid=np.array(TEST_ASK_SECOND_GRID),
        )
        assert len(metrics.sigma_timeline) == 2
        assert len(metrics.moneyness_grid) == 3

    def test_frozen(self) -> None:
        """Test that PathMetrics is frozen (immutable)."""
        metrics = PathMetrics(
            sigma_timeline=np.array(TEST_SIGMA_TIMELINE_ONE),
            sigma_mid_mean=np.array(TEST_SIGMA_MID_MEAN),
            sigma_mid_p95=np.array(TEST_SIGMA_MID_P95),
            moneyness_grid=np.array(TEST_MONEYNESS_GRID_ONE),
            forward_curve=np.array(TEST_FORWARD_CURVE_ONE),
            bid_second_grid=np.array(TEST_BID_SECOND_GRID),
            ask_second_grid=np.array(TEST_ASK_SECOND_GRID),
        )
        try:
            metrics.sigma_timeline = np.array(TEST_SIGMA_TIMELINE_MODIFIED)
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
