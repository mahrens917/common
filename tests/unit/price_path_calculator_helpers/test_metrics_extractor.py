"""Tests for price_path_calculator_helpers.metrics_extractor module."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from common.price_path_calculator_helpers.metrics_extractor import (
    MetricsExtractor,
    PathMetrics,
    PricePathComputationError,
)

# Test constants for PathMetrics
SIGMA_TIMELINE_TWO_ELEMENTS = (0.1, 0.2)
SIGMA_MID_MEAN_SINGLE = (0.15,)
SIGMA_MID_P95_SINGLE = (0.2,)
MONEYNESS_GRID_THREE_ELEMENTS = (0.9, 1.0, 1.1)
MONEYNESS_GRID_SINGLE = (1.0,)
FORWARD_CURVE_TWO_ELEMENTS = (100.0, 101.0)
FORWARD_CURVE_SINGLE = (100.0,)
BID_SECOND_GRID_2X2 = ((0.1, 0.2), (0.3, 0.4))
BID_SECOND_GRID_SINGLE = ((0.1,),)
ASK_SECOND_GRID_2X2 = ((0.2, 0.3), (0.4, 0.5))
ASK_SECOND_GRID_SINGLE = ((0.2,),)
SIGMA_TIMELINE_SINGLE = (0.1,)
SIGMA_TIMELINE_ASSERTION = (0.5,)


class TestPathMetrics:
    """Tests for PathMetrics dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test stores all fields."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_TWO_ELEMENTS),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_SINGLE),
            sigma_mid_p95=np.array(SIGMA_MID_P95_SINGLE),
            moneyness_grid=np.array(MONEYNESS_GRID_THREE_ELEMENTS),
            forward_curve=np.array(FORWARD_CURVE_TWO_ELEMENTS),
            bid_second_grid=np.array(BID_SECOND_GRID_2X2),
            ask_second_grid=np.array(ASK_SECOND_GRID_2X2),
        )

        assert len(metrics.sigma_timeline) == 2
        assert len(metrics.forward_curve) == 2

    def test_is_frozen(self) -> None:
        """Test dataclass is frozen."""
        metrics = PathMetrics(
            sigma_timeline=np.array(SIGMA_TIMELINE_SINGLE),
            sigma_mid_mean=np.array(SIGMA_MID_MEAN_SINGLE),
            sigma_mid_p95=np.array(SIGMA_MID_P95_SINGLE),
            moneyness_grid=np.array(MONEYNESS_GRID_SINGLE),
            forward_curve=np.array(FORWARD_CURVE_SINGLE),
            bid_second_grid=np.array(BID_SECOND_GRID_SINGLE),
            ask_second_grid=np.array(ASK_SECOND_GRID_SINGLE),
        )

        with pytest.raises(AttributeError):
            metrics.sigma_timeline = np.array(SIGMA_TIMELINE_ASSERTION)


class TestPricePathComputationError:
    """Tests for PricePathComputationError exception."""

    def test_is_exception(self) -> None:
        """Test is an Exception subclass."""
        error = PricePathComputationError("test error")
        assert isinstance(error, Exception)

    def test_stores_message(self) -> None:
        """Test stores error message."""
        error = PricePathComputationError("computation failed")
        assert str(error) == "computation failed"


class TestMetricsExtractorExtractPathMetrics:
    """Tests for extract_path_metrics method."""

    def test_extracts_all_metrics(self) -> None:
        """Test extracts all required metrics."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = {
            "timeline_years": [0.1, 0.2, 0.3],
            "mid_sigma_mean": [0.15, 0.16],
            "mid_sigma_p95": [0.2, 0.21],
            "moneyness_grid": [0.9, 1.0, 1.1],
            "forward_curve": [100.0, 101.0],
            "bid_second": [[0.1, 0.2, 0.3], [0.15, 0.25, 0.35]],
            "ask_second": [[0.2, 0.3, 0.4], [0.25, 0.35, 0.45]],
        }

        extractor = MetricsExtractor()
        result = extractor.extract_path_metrics(mock_surface, "BTC")

        assert len(result.sigma_timeline) == 3
        assert len(result.sigma_mid_mean) == 2
        assert len(result.forward_curve) == 2

    def test_raises_on_missing_precomputed_metrics(self) -> None:
        """Test raises when precomputed_path_metrics is missing."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = None

        extractor = MetricsExtractor()

        with pytest.raises(PricePathComputationError) as exc_info:
            extractor.extract_path_metrics(mock_surface, "BTC")

        assert "missing precomputed path metrics" in str(exc_info.value)

    def test_raises_on_missing_timeline(self) -> None:
        """Test raises when timeline_years is missing."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = {
            "mid_sigma_mean": [0.15],
            "mid_sigma_p95": [0.2],
            "moneyness_grid": [1.0],
            "forward_curve": [100.0],
            "bid_second": [[0.1]],
            "ask_second": [[0.2]],
        }

        extractor = MetricsExtractor()

        with pytest.raises(PricePathComputationError) as exc_info:
            extractor.extract_path_metrics(mock_surface, "BTC")

        assert "timeline" in str(exc_info.value).lower()

    def test_raises_on_empty_sigma_metadata(self) -> None:
        """Test raises when sigma metadata is empty."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = {
            "timeline_years": [0.1],
            "mid_sigma_mean": [],  # Empty
            "mid_sigma_p95": [0.2],
            "moneyness_grid": [1.0],
            "forward_curve": [100.0],
            "bid_second": [[0.1]],
            "ask_second": [[0.2]],
        }

        extractor = MetricsExtractor()

        with pytest.raises(PricePathComputationError) as exc_info:
            extractor.extract_path_metrics(mock_surface, "BTC")

        # Empty arrays are caught by _require_metric_array with "Missing sigma metadata"
        assert "sigma" in str(exc_info.value).lower()

    def test_raises_on_inconsistent_grid_dimensions(self) -> None:
        """Test raises when grid dimensions are inconsistent."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = {
            "timeline_years": [0.1],
            "mid_sigma_mean": [0.15],
            "mid_sigma_p95": [0.2],
            "moneyness_grid": [1.0],
            "forward_curve": [100.0, 101.0, 102.0],  # 3 elements
            "bid_second": [[0.1], [0.2]],  # 2x1 shape
            "ask_second": [[0.2], [0.3]],  # 2x1 shape
        }

        extractor = MetricsExtractor()

        with pytest.raises(PricePathComputationError) as exc_info:
            extractor.extract_path_metrics(mock_surface, "BTC")

        assert "dimensions inconsistent" in str(exc_info.value)

    def test_raises_on_bid_ask_shape_mismatch(self) -> None:
        """Test raises when bid and ask grids have different shapes."""
        mock_surface = MagicMock()
        mock_surface.precomputed_path_metrics = {
            "timeline_years": [0.1],
            "mid_sigma_mean": [0.15],
            "mid_sigma_p95": [0.2],
            "moneyness_grid": [1.0],
            "forward_curve": [100.0, 101.0],
            "bid_second": [[0.1, 0.2], [0.3, 0.4]],  # 2x2
            "ask_second": [[0.2, 0.3, 0.4], [0.5, 0.6, 0.7]],  # 2x3
        }

        extractor = MetricsExtractor()

        with pytest.raises(PricePathComputationError) as exc_info:
            extractor.extract_path_metrics(mock_surface, "BTC")

        assert "dimensions inconsistent" in str(exc_info.value)


class TestMetricsExtractorRequireMetricArray:
    """Tests for _require_metric_array static method."""

    def test_extracts_existing_key(self) -> None:
        """Test extracts array for existing key."""
        metrics = {"timeline": [0.1, 0.2, 0.3]}

        result = MetricsExtractor._require_metric_array(metrics, "timeline", "Missing timeline")

        assert isinstance(result, np.ndarray)
        assert len(result) == 3

    def test_raises_on_missing_key(self) -> None:
        """Test raises when key is missing."""
        metrics = {}

        with pytest.raises(PricePathComputationError) as exc_info:
            MetricsExtractor._require_metric_array(metrics, "missing_key", "Missing required metric")

        assert "Missing required metric" in str(exc_info.value)

    def test_raises_on_empty_array(self) -> None:
        """Test raises when array is empty."""
        metrics = {"empty_key": []}

        with pytest.raises(PricePathComputationError) as exc_info:
            MetricsExtractor._require_metric_array(metrics, "empty_key", "Empty array error")

        assert "Empty array error" in str(exc_info.value)

    def test_converts_to_float_dtype(self) -> None:
        """Test converts array to float dtype."""
        metrics = {"int_data": [1, 2, 3]}

        result = MetricsExtractor._require_metric_array(metrics, "int_data", "Error")

        assert result.dtype == float

    def test_handles_nested_lists(self) -> None:
        """Test handles nested lists (2D arrays)."""
        metrics = {"matrix": [[1, 2], [3, 4]]}

        result = MetricsExtractor._require_metric_array(metrics, "matrix", "Error")

        assert result.shape == (2, 2)
        assert result.dtype == float
