"""Tests for chart_components.prediction_overlay module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from common.chart_components.prediction_overlay import (
    PredictionOverlayParams,
    PredictionOverlayResult,
    UncertaintyEnvelopeParams,
    _build_envelope_colors,
    _build_sigma_array,
    _collect_uncertainty_extrema,
    _compute_envelope_bounds,
    _draw_prediction_line,
    _extract_historical_anchor,
    _merge_prediction_series,
    _plot_uncertainty_bands,
    _render_uncertainty_envelopes,
    _resolve_plot_series,
    _validate_uncertainty_inputs,
    collect_prediction_extrema,
    render_prediction_overlay,
    render_prediction_overlay_if_needed,
)

# Test constants for prediction overlay
TEST_HISTORICAL_TIMESTAMPS = [
    datetime(2025, 1, 1, 0, 0, 0),
    datetime(2025, 1, 1, 1, 0, 0),
    datetime(2025, 1, 1, 2, 0, 0),
]
TEST_HISTORICAL_VALUES = [10.0, 15.0, 20.0]
TEST_PREDICTION_TIMESTAMPS = [
    datetime(2025, 1, 1, 3, 0, 0),
    datetime(2025, 1, 1, 4, 0, 0),
]
TEST_PREDICTION_VALUES = [25.0, 30.0]
TEST_PREDICTION_UNCERTAINTIES = [2.0, 3.0]
TEST_PLOT_COLOR = "#FF0000"
TEST_ANCHOR_NUMERIC = 738887.08333333337
TEST_PREDICTION_NUMERIC = np.array([738887.125, 738887.16666666663])
TEST_MERGED_NUMERIC = np.array([738887.08333333337, 738887.125, 738887.16666666663])
TEST_MERGED_VALUES = np.array([20.0, 25.0, 30.0])
TEST_SIGMA_ARRAY = np.array([0.0, 2.0, 3.0])


class TestPredictionOverlayResult:
    """Tests for PredictionOverlayResult dataclass."""

    def test_initialization(self) -> None:
        """Test dataclass initialization."""
        result = PredictionOverlayResult(extrema=[10.0, 20.0, 30.0])
        assert result.extrema == [10.0, 20.0, 30.0]

    def test_frozen(self) -> None:
        """Test that dataclass is frozen."""
        result = PredictionOverlayResult(extrema=[10.0])
        with pytest.raises(AttributeError):
            result.extrema = [20.0]


class TestExtractHistoricalAnchor:
    """Tests for _extract_historical_anchor function."""

    def test_with_timestamps_and_values(self) -> None:
        """Test extraction with valid timestamps and values."""
        anchor_numeric, anchor_value = _extract_historical_anchor(
            TEST_HISTORICAL_TIMESTAMPS,
            TEST_HISTORICAL_VALUES,
        )
        assert anchor_numeric is not None
        assert anchor_value == 20.0

    def test_with_empty_timestamps(self) -> None:
        """Test with empty timestamps."""
        anchor_numeric, anchor_value = _extract_historical_anchor([], [])
        assert anchor_numeric is None
        assert anchor_value is None

    def test_with_timezone_aware_timestamp(self) -> None:
        """Test with timezone-aware timestamp."""
        tz_aware = [datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)]
        anchor_numeric, anchor_value = _extract_historical_anchor(tz_aware, [15.0])
        assert anchor_numeric is not None
        assert anchor_value == 15.0

    def test_with_empty_values(self) -> None:
        """Test with timestamps but empty values."""
        anchor_numeric, anchor_value = _extract_historical_anchor(
            TEST_HISTORICAL_TIMESTAMPS,
            [],
        )
        assert anchor_numeric is not None
        assert anchor_value is None


class TestMergePredictionSeries:
    """Tests for _merge_prediction_series function."""

    def test_with_anchor(self) -> None:
        """Test merging with anchor."""
        merged_numeric, merged_values = _merge_prediction_series(
            anchor_numeric=100.0,
            anchor_value=20.0,
            prediction_numeric=np.array([101.0, 102.0]),
            prediction_values=[25.0, 30.0],
        )
        assert merged_numeric[0] == 100.0
        assert merged_values[0] == 20.0
        assert len(merged_numeric) == 3
        assert len(merged_values) == 3

    def test_without_anchor(self) -> None:
        """Test merging without anchor."""
        prediction_numeric = np.array([101.0, 102.0])
        prediction_values = [25.0, 30.0]
        merged_numeric, merged_values = _merge_prediction_series(
            anchor_numeric=None,
            anchor_value=None,
            prediction_numeric=prediction_numeric,
            prediction_values=prediction_values,
        )
        np.testing.assert_array_equal(merged_numeric, prediction_numeric)
        np.testing.assert_array_equal(merged_values, prediction_values)

    def test_with_anchor_no_value(self) -> None:
        """Test merging with anchor but no anchor value."""
        merged_numeric, merged_values = _merge_prediction_series(
            anchor_numeric=100.0,
            anchor_value=None,
            prediction_numeric=np.array([101.0, 102.0]),
            prediction_values=[25.0, 30.0],
        )
        assert merged_values[0] == 25.0


class TestDrawPredictionLine:
    """Tests for _draw_prediction_line function."""

    def test_draws_line(self) -> None:
        """Test that line is drawn."""
        mock_ax = MagicMock()
        numeric = np.array([1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0])

        _draw_prediction_line(mock_ax, numeric, values, TEST_PLOT_COLOR)

        mock_ax.plot.assert_called_once()
        call_args = mock_ax.plot.call_args
        np.testing.assert_array_equal(call_args[0][0], numeric)
        np.testing.assert_array_equal(call_args[0][1], values)
        assert call_args[1]["color"] == TEST_PLOT_COLOR


class TestValidateUncertaintyInputs:
    """Tests for _validate_uncertainty_inputs function."""

    def test_valid_inputs(self) -> None:
        """Test with matching lengths."""
        _validate_uncertainty_inputs([1.0, 2.0], [0.5, 1.0])

    def test_mismatched_lengths(self) -> None:
        """Test with mismatched lengths."""
        with pytest.raises(ValueError, match="prediction_uncertainties must match prediction_values length"):
            _validate_uncertainty_inputs([1.0, 2.0], [0.5])


class TestUncertaintyEnvelopeParams:
    """Tests for UncertaintyEnvelopeParams dataclass."""

    def test_initialization(self) -> None:
        """Test dataclass initialization."""
        params = UncertaintyEnvelopeParams(
            anchor_numeric=100.0,
            prediction_numeric=np.array([101.0]),
            merged_numeric=np.array([100.0, 101.0]),
            merged_values=np.array([20.0, 25.0]),
            prediction_values=[25.0],
            prediction_uncertainties=[2.0],
            plot_color=TEST_PLOT_COLOR,
        )
        assert params.anchor_numeric == 100.0
        assert params.plot_color == TEST_PLOT_COLOR

    def test_frozen(self) -> None:
        """Test that dataclass is frozen."""
        params = UncertaintyEnvelopeParams(
            anchor_numeric=100.0,
            prediction_numeric=np.array([101.0]),
            merged_numeric=np.array([100.0, 101.0]),
            merged_values=np.array([20.0, 25.0]),
            prediction_values=[25.0],
            prediction_uncertainties=[2.0],
            plot_color=TEST_PLOT_COLOR,
        )
        with pytest.raises(AttributeError):
            params.plot_color = "#00FF00"


class TestBuildSigmaArray:
    """Tests for _build_sigma_array function."""

    def test_with_anchor(self) -> None:
        """Test with anchor."""
        result = _build_sigma_array(100.0, [1.0, 2.0, 3.0])
        assert len(result) == 4
        assert result[0] == 0.0

    def test_without_anchor(self) -> None:
        """Test without anchor."""
        result = _build_sigma_array(None, [1.0, 2.0, 3.0])
        assert len(result) == 3
        np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])


class TestResolvePlotSeries:
    """Tests for _resolve_plot_series function."""

    def test_with_anchor(self) -> None:
        """Test with anchor."""
        merged_numeric = np.array([100.0, 101.0])
        merged_values = np.array([20.0, 25.0])
        numeric, values = _resolve_plot_series(
            anchor_numeric=100.0,
            prediction_numeric=np.array([101.0]),
            merged_numeric=merged_numeric,
            merged_values=merged_values,
            prediction_values=[25.0],
        )
        np.testing.assert_array_equal(numeric, merged_numeric)
        np.testing.assert_array_equal(values, merged_values)

    def test_without_anchor(self) -> None:
        """Test without anchor."""
        prediction_numeric = np.array([101.0])
        prediction_values = [25.0]
        numeric, values = _resolve_plot_series(
            anchor_numeric=None,
            prediction_numeric=prediction_numeric,
            merged_numeric=np.array([100.0, 101.0]),
            merged_values=np.array([20.0, 25.0]),
            prediction_values=prediction_values,
        )
        np.testing.assert_array_equal(numeric, prediction_numeric)
        np.testing.assert_array_equal(values, prediction_values)


class TestBuildEnvelopeColors:
    """Tests for _build_envelope_colors function."""

    def test_returns_color_dict(self) -> None:
        """Test returns color dictionary."""
        colors = _build_envelope_colors(TEST_PLOT_COLOR)
        assert "sigma1_fill" in colors
        assert "sigma2_fill" in colors
        assert "sigma2_line" in colors

    def test_sigma1_alpha(self) -> None:
        """Test sigma1 fill has correct alpha."""
        colors = _build_envelope_colors(TEST_PLOT_COLOR)
        assert colors["sigma1_fill"][3] == 0.30

    def test_sigma2_alpha(self) -> None:
        """Test sigma2 fill has correct alpha."""
        colors = _build_envelope_colors(TEST_PLOT_COLOR)
        assert colors["sigma2_fill"][3] == 0.18


class TestComputeEnvelopeBounds:
    """Tests for _compute_envelope_bounds function."""

    def test_computes_bounds(self) -> None:
        """Test computes all bounds."""
        values = np.array([10.0, 20.0])
        sigma = np.array([1.0, 2.0])
        bounds = _compute_envelope_bounds(values, sigma)

        assert "sigma1_upper" in bounds
        assert "sigma1_lower" in bounds
        assert "sigma2_upper" in bounds
        assert "sigma2_lower" in bounds

        np.testing.assert_array_equal(bounds["sigma1_upper"], [11.0, 22.0])
        np.testing.assert_array_equal(bounds["sigma1_lower"], [9.0, 18.0])
        np.testing.assert_array_equal(bounds["sigma2_upper"], [12.0, 24.0])
        np.testing.assert_array_equal(bounds["sigma2_lower"], [8.0, 16.0])


class TestPlotUncertaintyBands:
    """Tests for _plot_uncertainty_bands function."""

    def test_draws_bands_and_lines(self) -> None:
        """Test draws fill_between and plot calls."""
        mock_ax = MagicMock()
        numeric = np.array([1.0, 2.0, 3.0])
        envelopes = {
            "sigma1_upper": np.array([11.0, 21.0, 31.0]),
            "sigma1_lower": np.array([9.0, 19.0, 29.0]),
            "sigma2_upper": np.array([12.0, 22.0, 32.0]),
            "sigma2_lower": np.array([8.0, 18.0, 28.0]),
        }
        colors = {
            "sigma1_fill": (0.7, 0.7, 0.7, 0.30),
            "sigma2_fill": (0.3, 0.3, 0.4, 0.18),
            "sigma2_line": "#475569",
        }

        _plot_uncertainty_bands(mock_ax, numeric, envelopes, colors, TEST_PLOT_COLOR)

        assert mock_ax.fill_between.call_count == 2
        assert mock_ax.plot.call_count == 4


class TestCollectUncertaintyExtrema:
    """Tests for _collect_uncertainty_extrema function."""

    def test_collects_extrema(self) -> None:
        """Test collects extrema."""
        result = _collect_uncertainty_extrema([10.0, 20.0], [1.0, 2.0])
        assert len(result) == 4
        assert 11.0 in result
        assert 9.0 in result
        assert 22.0 in result
        assert 18.0 in result


class TestRenderUncertaintyEnvelopes:
    """Tests for _render_uncertainty_envelopes function."""

    @patch("common.chart_components.prediction_overlay._plot_uncertainty_bands")
    @patch("common.chart_components.prediction_overlay._compute_envelope_bounds")
    @patch("common.chart_components.prediction_overlay._build_envelope_colors")
    @patch("common.chart_components.prediction_overlay._resolve_plot_series")
    @patch("common.chart_components.prediction_overlay._build_sigma_array")
    def test_renders_envelopes(
        self,
        mock_build_sigma: MagicMock,
        mock_resolve: MagicMock,
        mock_colors: MagicMock,
        mock_bounds: MagicMock,
        mock_plot: MagicMock,
    ) -> None:
        """Test renders uncertainty envelopes."""
        mock_ax = MagicMock()
        mock_build_sigma.return_value = np.array([0.0, 1.0, 2.0])
        mock_resolve.return_value = (np.array([1.0, 2.0]), np.array([10.0, 20.0]))
        mock_colors.return_value = {
            "sigma1_fill": (0.7, 0.7, 0.7, 0.30),
            "sigma2_fill": (0.3, 0.3, 0.4, 0.18),
            "sigma2_line": "#475569",
        }
        mock_bounds.return_value = {
            "sigma1_upper": np.array([11.0]),
            "sigma1_lower": np.array([9.0]),
            "sigma2_upper": np.array([12.0]),
            "sigma2_lower": np.array([8.0]),
        }

        params = UncertaintyEnvelopeParams(
            anchor_numeric=100.0,
            prediction_numeric=np.array([101.0, 102.0]),
            merged_numeric=np.array([100.0, 101.0, 102.0]),
            merged_values=np.array([10.0, 20.0, 30.0]),
            prediction_values=[20.0, 30.0],
            prediction_uncertainties=[1.0, 2.0],
            plot_color=TEST_PLOT_COLOR,
        )

        result = _render_uncertainty_envelopes(mock_ax, params)

        mock_build_sigma.assert_called_once()
        mock_resolve.assert_called_once()
        mock_colors.assert_called_once()
        mock_bounds.assert_called_once()
        mock_plot.assert_called_once()
        assert len(result) == 4


class TestRenderPredictionOverlay:
    """Tests for render_prediction_overlay function."""

    @patch("common.chart_components.prediction_overlay.mdates")
    def test_empty_predictions(self, mock_mdates: MagicMock) -> None:
        """Test with no predictions."""
        mock_ax = MagicMock()
        result = render_prediction_overlay(
            ax=mock_ax,
            historical_timestamps=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            prediction_timestamps=None,
            prediction_values=None,
            prediction_uncertainties=None,
            plot_color=TEST_PLOT_COLOR,
        )
        assert result.extrema == []
        mock_ax.plot.assert_not_called()

    @patch("common.chart_components.prediction_overlay.mdates")
    def test_mismatched_lengths(self, mock_mdates: MagicMock) -> None:
        """Test with mismatched prediction lengths."""
        mock_ax = MagicMock()
        with pytest.raises(ValueError, match="prediction_timestamps and prediction_values must have the same length"):
            render_prediction_overlay(
                ax=mock_ax,
                historical_timestamps=TEST_HISTORICAL_TIMESTAMPS,
                historical_values=TEST_HISTORICAL_VALUES,
                prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
                prediction_values=[25.0],
                prediction_uncertainties=None,
                plot_color=TEST_PLOT_COLOR,
            )

    @patch("common.chart_components.prediction_overlay._draw_prediction_line")
    @patch("common.chart_components.prediction_overlay.mdates")
    def test_without_uncertainties(
        self,
        mock_mdates: MagicMock,
        mock_draw: MagicMock,
    ) -> None:
        """Test rendering without uncertainties."""
        mock_ax = MagicMock()

        def date2num_side_effect(arg):
            if isinstance(arg, list):
                return np.array([738887.125, 738887.16666666663])
            return 738887.08333333337

        mock_mdates.date2num.side_effect = date2num_side_effect

        result = render_prediction_overlay(
            ax=mock_ax,
            historical_timestamps=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=None,
            plot_color=TEST_PLOT_COLOR,
        )

        assert len(result.extrema) == 2
        mock_draw.assert_called_once()

    @patch("common.chart_components.prediction_overlay._render_uncertainty_envelopes")
    @patch("common.chart_components.prediction_overlay._draw_prediction_line")
    @patch("common.chart_components.prediction_overlay.mdates")
    def test_with_uncertainties(
        self,
        mock_mdates: MagicMock,
        mock_draw: MagicMock,
        mock_render_envelopes: MagicMock,
    ) -> None:
        """Test rendering with uncertainties."""
        mock_ax = MagicMock()

        def date2num_side_effect(arg):
            if isinstance(arg, list):
                return np.array([738887.125, 738887.16666666663])
            return 738887.08333333337

        mock_mdates.date2num.side_effect = date2num_side_effect
        mock_render_envelopes.return_value = [27.0, 23.0, 33.0, 27.0]

        result = render_prediction_overlay(
            ax=mock_ax,
            historical_timestamps=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=TEST_PREDICTION_UNCERTAINTIES,
            plot_color=TEST_PLOT_COLOR,
        )

        assert len(result.extrema) == 6
        mock_draw.assert_called_once()
        mock_render_envelopes.assert_called_once()


class TestPredictionOverlayParams:
    """Tests for PredictionOverlayParams dataclass."""

    def test_initialization(self) -> None:
        """Test dataclass initialization."""
        params = PredictionOverlayParams(
            historical_naive=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            precomputed_prediction=None,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=TEST_PREDICTION_UNCERTAINTIES,
            plot_color=TEST_PLOT_COLOR,
        )
        assert params.plot_color == TEST_PLOT_COLOR

    def test_frozen(self) -> None:
        """Test that dataclass is frozen."""
        params = PredictionOverlayParams(
            historical_naive=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            precomputed_prediction=None,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=TEST_PREDICTION_UNCERTAINTIES,
            plot_color=TEST_PLOT_COLOR,
        )
        with pytest.raises(AttributeError):
            params.plot_color = "#00FF00"


class TestRenderPredictionOverlayIfNeeded:
    """Tests for render_prediction_overlay_if_needed function."""

    def test_no_predictions(self) -> None:
        """Test with no predictions."""
        mock_ax = MagicMock()
        params = PredictionOverlayParams(
            historical_naive=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            precomputed_prediction=None,
            prediction_timestamps=None,
            prediction_values=None,
            prediction_uncertainties=None,
            plot_color=TEST_PLOT_COLOR,
        )
        result = render_prediction_overlay_if_needed(ax=mock_ax, params=params)
        assert result.extrema == []

    @patch("common.chart_components.prediction_overlay.render_prediction_overlay")
    def test_with_precomputed_prediction(self, mock_render: MagicMock) -> None:
        """Test with precomputed prediction timestamps."""
        mock_ax = MagicMock()
        mock_render.return_value = PredictionOverlayResult(extrema=[25.0, 30.0])
        precomputed = TEST_PREDICTION_TIMESTAMPS

        params = PredictionOverlayParams(
            historical_naive=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            precomputed_prediction=precomputed,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=None,
            plot_color=TEST_PLOT_COLOR,
        )

        result = render_prediction_overlay_if_needed(ax=mock_ax, params=params)

        mock_render.assert_called_once()
        assert result.extrema == [25.0, 30.0]

    @patch("common.chart_components.prediction_overlay.render_prediction_overlay")
    @patch("common.chart_components.prediction_overlay.ensure_naive_timestamps")
    def test_without_precomputed_prediction(
        self,
        mock_ensure_naive: MagicMock,
        mock_render: MagicMock,
    ) -> None:
        """Test without precomputed prediction timestamps."""
        mock_ax = MagicMock()
        mock_ensure_naive.return_value = TEST_PREDICTION_TIMESTAMPS
        mock_render.return_value = PredictionOverlayResult(extrema=[25.0, 30.0])

        params = PredictionOverlayParams(
            historical_naive=TEST_HISTORICAL_TIMESTAMPS,
            historical_values=TEST_HISTORICAL_VALUES,
            precomputed_prediction=None,
            prediction_timestamps=TEST_PREDICTION_TIMESTAMPS,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=None,
            plot_color=TEST_PLOT_COLOR,
        )

        result = render_prediction_overlay_if_needed(ax=mock_ax, params=params)

        mock_ensure_naive.assert_called_once()
        mock_render.assert_called_once()
        assert result.extrema == [25.0, 30.0]


class TestCollectPredictionExtrema:
    """Tests for collect_prediction_extrema function."""

    def test_with_overlay_extrema(self) -> None:
        """Test with overlay result containing extrema."""
        overlay_result = PredictionOverlayResult(extrema=[10.0, 20.0, 30.0])
        result = collect_prediction_extrema(
            overlay_result=overlay_result,
            prediction_values=TEST_PREDICTION_VALUES,
            prediction_uncertainties=TEST_PREDICTION_UNCERTAINTIES,
        )
        assert result == [10.0, 20.0, 30.0]

    def test_without_overlay_extrema_with_uncertainties(self) -> None:
        """Test without overlay extrema but with uncertainties."""
        overlay_result = PredictionOverlayResult(extrema=[])
        result = collect_prediction_extrema(
            overlay_result=overlay_result,
            prediction_values=[10.0, 20.0],
            prediction_uncertainties=[1.0, 2.0],
        )
        assert 10.0 in result
        assert 20.0 in result
        assert 11.0 in result
        assert 9.0 in result
        assert 22.0 in result
        assert 18.0 in result

    def test_without_overlay_extrema_without_uncertainties(self) -> None:
        """Test without overlay extrema and without uncertainties."""
        overlay_result = PredictionOverlayResult(extrema=[])
        result = collect_prediction_extrema(
            overlay_result=overlay_result,
            prediction_values=[10.0, 20.0],
            prediction_uncertainties=None,
        )
        assert result == [10.0, 20.0]

    def test_with_empty_predictions(self) -> None:
        """Test with empty prediction values."""
        overlay_result = PredictionOverlayResult(extrema=[])
        result = collect_prediction_extrema(
            overlay_result=overlay_result,
            prediction_values=None,
            prediction_uncertainties=None,
        )
        assert result == []
