"""Tests for chart_generator_helpers.series_statistics_calculator module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator_helpers.series_statistics_calculator import (
    SeriesStatisticsCalculator,
)


class TestSeriesStatisticsCalculatorInit:
    """Tests for SeriesStatisticsCalculator initialization."""

    def test_creates_instance(self) -> None:
        """Test creates instance."""
        calculator = SeriesStatisticsCalculator()
        assert calculator is not None


class TestSeriesStatisticsCalculatorComputeSeriesStatistics:
    """Tests for compute_series_statistics method."""

    def test_computes_min_value(self) -> None:
        """Test computes minimum value."""
        mock_np = MagicMock()
        mock_np.min.return_value = 10.0
        mock_np.max.return_value = 90.0
        mock_np.mean.return_value = 50.0

        calculator = SeriesStatisticsCalculator()
        result = calculator.compute_series_statistics([10.0, 50.0, 90.0], mock_np)

        assert result.min_value == 10.0

    def test_computes_max_value(self) -> None:
        """Test computes maximum value."""
        mock_np = MagicMock()
        mock_np.min.return_value = 10.0
        mock_np.max.return_value = 90.0
        mock_np.mean.return_value = 50.0

        calculator = SeriesStatisticsCalculator()
        result = calculator.compute_series_statistics([10.0, 50.0, 90.0], mock_np)

        assert result.max_value == 90.0

    def test_computes_mean_value(self) -> None:
        """Test computes mean value."""
        mock_np = MagicMock()
        mock_np.min.return_value = 10.0
        mock_np.max.return_value = 90.0
        mock_np.mean.return_value = 50.0

        calculator = SeriesStatisticsCalculator()
        result = calculator.compute_series_statistics([10.0, 50.0, 90.0], mock_np)

        assert result.mean_value == 50.0

    def test_returns_chart_statistics_object(self) -> None:
        """Test returns ChartStatistics object."""
        mock_np = MagicMock()
        mock_np.min.return_value = 0.0
        mock_np.max.return_value = 100.0
        mock_np.mean.return_value = 50.0

        calculator = SeriesStatisticsCalculator()
        result = calculator.compute_series_statistics([0.0, 100.0], mock_np)

        assert hasattr(result, "min_value")
        assert hasattr(result, "max_value")
        assert hasattr(result, "mean_value")

    def test_raises_on_empty_values(self) -> None:
        """Test raises InsufficientDataError when numpy raises ValueError."""
        from common.chart_generator.exceptions import InsufficientDataError

        mock_np = MagicMock()
        mock_np.min.side_effect = ValueError("empty sequence")

        calculator = SeriesStatisticsCalculator()

        with pytest.raises(InsufficientDataError) as exc_info:
            calculator.compute_series_statistics([], mock_np)

        assert "Cannot compute statistics without values" in str(exc_info.value)

    def test_converts_to_float(self) -> None:
        """Test converts numpy values to float."""
        mock_np = MagicMock()
        mock_np.min.return_value = 5
        mock_np.max.return_value = 15
        mock_np.mean.return_value = 10

        calculator = SeriesStatisticsCalculator()
        result = calculator.compute_series_statistics([5, 10, 15], mock_np)

        assert isinstance(result.min_value, float)
        assert isinstance(result.max_value, float)
        assert isinstance(result.mean_value, float)

    def test_passes_values_to_numpy_functions(self) -> None:
        """Test passes values list to numpy functions."""
        mock_np = MagicMock()
        mock_np.min.return_value = 1.0
        mock_np.max.return_value = 3.0
        mock_np.mean.return_value = 2.0

        values = [1.0, 2.0, 3.0]
        calculator = SeriesStatisticsCalculator()
        calculator.compute_series_statistics(values, mock_np)

        mock_np.min.assert_called_once_with(values)
        mock_np.max.assert_called_once_with(values)
        mock_np.mean.assert_called_once_with(values)
