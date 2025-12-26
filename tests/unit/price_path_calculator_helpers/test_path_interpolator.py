"""Tests for price_path_calculator_helpers.path_interpolator module."""

import numpy as np
import pytest

from common.price_path_calculator_helpers.metrics_extractor import PathMetrics
from common.price_path_calculator_helpers.path_interpolator import PathInterpolator

# Test constants for data_guard compliance
SIGMA_TIMELINE_BASIC = (0.0, 0.5, 1.0)
SIGMA_MID_MEAN_BASIC = (0.1, 0.2, 0.3)
SIGMA_MID_P95_BASIC = (0.15, 0.25, 0.35)
SIGMA_MID_P95_SIZE_MISMATCH = (0.15, 0.25)
MONEYNESS_GRID_SINGLE = (1.0,)
FORWARD_CURVE_BASIC = (100.0, 105.0, 110.0)
BID_SECOND_GRID_SINGLE = ((0.1,),)
ASK_SECOND_GRID_SINGLE = ((0.2,),)
TIMELINE_FIVE_POINTS = (0.0, 0.25, 0.5, 0.75, 1.0)
TIMELINE_THREE_POINTS = (0.0, 0.5, 1.0)
NORMALIZED_EXPECTATION_THREE = (1.0, 1.1, 1.2)
SIGMA_TIMELINE_LEFT_BOUNDARY = (0.5, 1.0)
SIGMA_MID_MEAN_LEFT_BOUNDARY = (0.2, 0.3)
FORWARD_CURVE_LEFT_BOUNDARY = (105.0, 110.0)
NORMALIZED_EXPECTATION_TWO = (1.1, 1.2)
SIGMA_TIMELINE_RIGHT_BOUNDARY = (0.0, 0.5)
SIGMA_MID_MEAN_RIGHT_BOUNDARY = (0.1, 0.2)
SIGMA_MID_P95_RIGHT_BOUNDARY = (0.15, 0.25)
FORWARD_CURVE_RIGHT_BOUNDARY = (100.0, 105.0)
NORMALIZED_EXPECTATION_TWO_START_ONE = (1.0, 1.1)
SIGMA_TIMELINE_TWO_POINTS = (0.0, 1.0)
SIGMA_MID_MEAN_TWO_POINTS = (0.1, 0.2)
SIGMA_MID_P95_TWO_POINTS = (0.15, 0.25)
FORWARD_CURVE_TWO_POINTS = (100.0, 110.0)


class TestPathInterpolatorInterpolatePathSeries:
    """Tests for interpolate_path_series method."""

    def test_interpolates_sigma(self) -> None:
        """Test interpolates sigma values."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_BASIC),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_BASIC),
            sigma_mid_p95=np.array(SIGMA_MID_P95_BASIC),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_BASIC),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_FIVE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_THREE)

        interpolator = PathInterpolator()
        sigma_interp, _, _, _ = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        assert len(sigma_interp) == 5
        assert sigma_interp[0] == pytest.approx(0.1)
        assert sigma_interp[2] == pytest.approx(0.2)  # At 0.5
        assert sigma_interp[4] == pytest.approx(0.3)

    def test_interpolates_sigma_p95(self) -> None:
        """Test interpolates sigma p95 values when sizes match."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_BASIC),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_BASIC),
            sigma_mid_p95=np.array(SIGMA_MID_P95_BASIC),  # Same size as sigma_timeline
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_BASIC),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_THREE)

        interpolator = PathInterpolator()
        _, sigma_p95_interp, _, _ = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        assert sigma_p95_interp[0] == pytest.approx(0.15)
        assert sigma_p95_interp[1] == pytest.approx(0.25)
        assert sigma_p95_interp[2] == pytest.approx(0.35)

    def test_fallback_sigma_p95_when_sizes_differ(self) -> None:
        """Test uses fallback sigma p95 (1.5x sigma) when sizes differ."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_BASIC),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_BASIC),
            sigma_mid_p95=np.array(SIGMA_MID_P95_SIZE_MISMATCH),  # Different size
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_BASIC),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_THREE)

        interpolator = PathInterpolator()
        sigma_interp, sigma_p95_interp, _, _ = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        # sigma_p95 should be 1.5x sigma
        np.testing.assert_array_almost_equal(sigma_p95_interp, sigma_interp * 1.5)

    def test_interpolates_expected(self) -> None:
        """Test interpolates expected values."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_BASIC),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_BASIC),
            sigma_mid_p95=np.array(SIGMA_MID_P95_BASIC),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_BASIC),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_THREE)

        interpolator = PathInterpolator()
        _, _, expected_interp, _ = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        assert expected_interp[0] == pytest.approx(1.0)
        assert expected_interp[1] == pytest.approx(1.1)
        assert expected_interp[2] == pytest.approx(1.2)

    def test_interpolates_forward(self) -> None:
        """Test interpolates forward curve."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_BASIC),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_BASIC),
            sigma_mid_p95=np.array(SIGMA_MID_P95_BASIC),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_BASIC),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_FIVE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_THREE)

        interpolator = PathInterpolator()
        _, _, _, forward_interp = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        assert len(forward_interp) == 5
        assert forward_interp[0] == pytest.approx(100.0)
        assert forward_interp[2] == pytest.approx(105.0)
        assert forward_interp[4] == pytest.approx(110.0)

    def test_extrapolates_left_boundary(self) -> None:
        """Test extrapolates using left boundary values."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_LEFT_BOUNDARY),  # Starts at 0.5
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_LEFT_BOUNDARY),
            sigma_mid_p95=np.array(SIGMA_MID_P95_BASIC),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_LEFT_BOUNDARY),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)  # 0.0 is before sigma_timeline start
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_TWO)

        interpolator = PathInterpolator()
        sigma_interp, _, _, forward_interp = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        # At 0.0, should use left boundary (first value)
        assert sigma_interp[0] == pytest.approx(0.2)
        assert forward_interp[0] == pytest.approx(105.0)

    def test_extrapolates_right_boundary(self) -> None:
        """Test extrapolates using right boundary values."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_RIGHT_BOUNDARY),  # Ends at 0.5
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_RIGHT_BOUNDARY),
            sigma_mid_p95=np.array(SIGMA_MID_P95_RIGHT_BOUNDARY),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_RIGHT_BOUNDARY),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)  # 1.0 is after sigma_timeline end
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_TWO_START_ONE)

        interpolator = PathInterpolator()
        sigma_interp, _, _, forward_interp = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        # At 1.0, should use right boundary (last value)
        assert sigma_interp[2] == pytest.approx(0.2)
        assert forward_interp[2] == pytest.approx(105.0)

    def test_returns_four_arrays(self) -> None:
        """Test returns tuple of four arrays."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_TWO_POINTS),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_TWO_POINTS),
            sigma_mid_p95=np.array(SIGMA_MID_P95_TWO_POINTS),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_TWO_POINTS),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )
        timeline = np.array(TIMELINE_THREE_POINTS)
        normalized_expectation = np.array(NORMALIZED_EXPECTATION_TWO_START_ONE)

        interpolator = PathInterpolator()
        result = interpolator.interpolate_path_series(
            timeline_years=timeline,
            metrics=metrics,
            normalized_expectation=normalized_expectation,
        )

        assert len(result) == 4
        for arr in result:
            assert isinstance(arr, np.ndarray)
            assert len(arr) == 3
