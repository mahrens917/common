"""Tests for chart_components.prediction_overlay_helpers module."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from common.chart_components.prediction_overlay_helpers import (
    collect_extrema,
    compute_band_colors,
    draw_uncertainty_bands,
    prepare_sigma_array,
    select_numeric_and_values,
)

# Test data arrays for prediction overlay tests
TEST_PREDICTION_NUMERIC = (1.0, 2.0)
TEST_PREDICTION_VALUES = (10.0, 20.0)
TEST_MERGED_NUMERIC = (0.0, 1.0, 2.0)
TEST_MERGED_VALUES = (5.0, 10.0, 20.0)
TEST_DRAW_NUMERIC = (1.0, 2.0, 3.0)
TEST_DRAW_VALUES = (10.0, 15.0, 20.0)
TEST_DRAW_SIGMA = (0.5, 1.0, 1.5)


class TestPrepareSigmaArray:
    """Tests for prepare_sigma_array function."""

    def test_with_anchor(self) -> None:
        """Test sigma array with anchor."""
        uncertainties = [0.5, 1.0, 1.5]
        result = prepare_sigma_array(1.0, uncertainties)

        assert len(result) == 4
        assert result[0] == 0.0

    def test_without_anchor(self) -> None:
        """Test sigma array without anchor."""
        uncertainties = [0.5, 1.0, 1.5]
        result = prepare_sigma_array(None, uncertainties)

        assert len(result) == 3
        np.testing.assert_array_almost_equal(result, uncertainties)

    def test_empty_uncertainties(self) -> None:
        """Test with empty uncertainties."""
        result = prepare_sigma_array(1.0, [])
        assert len(result) == 1
        assert result[0] == 0.0


class TestComputeBandColors:
    """Tests for compute_band_colors function."""

    def test_returns_two_colors(self) -> None:
        """Test returns two color tuples."""
        sigma1_color, sigma2_color = compute_band_colors("#FF0000")

        assert len(sigma1_color) == 4
        assert len(sigma2_color) == 4

    def test_sigma1_has_alpha(self) -> None:
        """Test sigma1 color has alpha 0.30."""
        sigma1_color, _ = compute_band_colors("#00FF00")
        assert sigma1_color[3] == 0.30

    def test_sigma2_has_alpha(self) -> None:
        """Test sigma2 color has alpha 0.18."""
        _, sigma2_color = compute_band_colors("#0000FF")
        assert sigma2_color[3] == 0.18

    def test_different_input_colors(self) -> None:
        """Test with different input colors."""
        result1 = compute_band_colors("#FF0000")
        result2 = compute_band_colors("#00FF00")

        assert result1[0][:3] != result2[0][:3]


class TestSelectNumericAndValues:
    """Tests for select_numeric_and_values function."""

    def test_with_anchor(self) -> None:
        """Test selects merged arrays when anchor present."""
        prediction_numeric = np.array(TEST_PREDICTION_NUMERIC)
        prediction_values = list(TEST_PREDICTION_VALUES)
        merged_numeric = np.array(TEST_MERGED_NUMERIC)
        merged_values = np.array(TEST_MERGED_VALUES)

        numeric, values = select_numeric_and_values(
            anchor_numeric=0.0,
            prediction_numeric=prediction_numeric,
            prediction_values=prediction_values,
            merged_numeric=merged_numeric,
            merged_values=merged_values,
        )

        np.testing.assert_array_equal(numeric, merged_numeric)
        np.testing.assert_array_equal(values, merged_values)

    def test_without_anchor(self) -> None:
        """Test selects prediction arrays when no anchor."""
        prediction_numeric = np.array(TEST_PREDICTION_NUMERIC)
        prediction_values = list(TEST_PREDICTION_VALUES)
        merged_numeric = np.array(TEST_MERGED_NUMERIC)
        merged_values = np.array(TEST_MERGED_VALUES)

        numeric, values = select_numeric_and_values(
            anchor_numeric=None,
            prediction_numeric=prediction_numeric,
            prediction_values=prediction_values,
            merged_numeric=merged_numeric,
            merged_values=merged_values,
        )

        np.testing.assert_array_equal(numeric, prediction_numeric)
        np.testing.assert_array_almost_equal(values, prediction_values)


class TestDrawUncertaintyBands:
    """Tests for draw_uncertainty_bands function."""

    def test_draws_bands_and_lines(self) -> None:
        """Test draws fill_between and plot calls."""
        mock_ax = MagicMock()
        numeric = np.array(TEST_DRAW_NUMERIC)
        values = np.array(TEST_DRAW_VALUES)
        sigma = np.array(TEST_DRAW_SIGMA)

        draw_uncertainty_bands(
            mock_ax,
            numeric,
            values,
            sigma,
            sigma1_color=(0.7, 0.7, 0.7, 0.30),
            sigma2_color=(0.3, 0.3, 0.4, 0.18),
            plot_color="#FF0000",
        )

        assert mock_ax.fill_between.call_count == 2
        assert mock_ax.plot.call_count == 4


class TestCollectExtrema:
    """Tests for collect_extrema function."""

    def test_collects_extrema(self) -> None:
        """Test collects upper and lower extrema."""
        values = [10.0, 20.0, 30.0]
        uncertainties = [1.0, 2.0, 3.0]

        result = collect_extrema(values, uncertainties)

        assert len(result) == 6
        assert 11.0 in result
        assert 9.0 in result
        assert 22.0 in result
        assert 18.0 in result
        assert 33.0 in result
        assert 27.0 in result

    def test_empty_inputs(self) -> None:
        """Test with empty inputs."""
        result = collect_extrema([], [])
        assert result == []

    def test_single_value(self) -> None:
        """Test with single value."""
        result = collect_extrema([100.0], [5.0])
        assert result == [105.0, 95.0]
