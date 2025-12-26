"""Tests for chart_generator_helpers.chart_axes_creator module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator_helpers.chart_axes_creator import ChartAxesCreator


class TestChartAxesCreator:
    """Tests for ChartAxesCreator class."""

    def test_init(self) -> None:
        """Test initialization."""
        creator = ChartAxesCreator(
            chart_width_inches=12.0,
            chart_height_inches=6.0,
            dpi=150.0,
            background_color="#1a1a2e",
        )

        assert creator.chart_width_inches == 12.0
        assert creator.chart_height_inches == 6.0
        assert creator.dpi == 150.0
        assert creator.background_color == "#1a1a2e"

    def test_create_chart_axes(self) -> None:
        """Test creates figure and axes."""
        creator = ChartAxesCreator(
            chart_width_inches=10.0,
            chart_height_inches=5.0,
            dpi=100.0,
            background_color="white",
        )
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        fig, ax = creator.create_chart_axes(mock_plt)

        assert fig == mock_fig
        assert ax == mock_ax
        mock_plt.subplots.assert_called_once_with(
            figsize=(10.0, 5.0),
            dpi=100.0,
            facecolor="white",
        )

    def test_cleanup_chart_figure(self) -> None:
        """Test cleans up figure."""
        creator = ChartAxesCreator(
            chart_width_inches=10.0,
            chart_height_inches=5.0,
            dpi=100.0,
            background_color="white",
        )
        mock_fig = MagicMock()
        mock_plt = MagicMock()

        creator.cleanup_chart_figure(mock_fig, mock_plt)

        mock_plt.close.assert_called_once_with(mock_fig)
        mock_plt.clf.assert_called_once()
        mock_plt.cla.assert_called_once()

    def test_cleanup_handles_close_error(self) -> None:
        """Test handles error during close."""
        creator = ChartAxesCreator(
            chart_width_inches=10.0,
            chart_height_inches=5.0,
            dpi=100.0,
            background_color="white",
        )
        mock_fig = MagicMock()
        mock_plt = MagicMock()
        mock_plt.close.side_effect = RuntimeError("Close failed")

        creator.cleanup_chart_figure(mock_fig, mock_plt)

        mock_plt.clf.assert_called_once()

    def test_cleanup_handles_clf_error(self) -> None:
        """Test handles error during clf."""
        creator = ChartAxesCreator(
            chart_width_inches=10.0,
            chart_height_inches=5.0,
            dpi=100.0,
            background_color="white",
        )
        mock_fig = MagicMock()
        mock_plt = MagicMock()
        mock_plt.clf.side_effect = ValueError("CLF failed")

        creator.cleanup_chart_figure(mock_fig, mock_plt)

        mock_plt.close.assert_called_once_with(mock_fig)
