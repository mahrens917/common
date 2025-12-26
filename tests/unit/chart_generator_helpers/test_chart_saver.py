"""Tests for chart_generator_helpers.chart_saver module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator_helpers.chart_saver import ChartSaver


class TestChartSaver:
    """Tests for ChartSaver class."""

    def test_init(self) -> None:
        """Test initialization."""
        saver = ChartSaver(dpi=150.0, background_color="#1a1a2e")

        assert saver.dpi == 150.0
        assert saver.background_color == "#1a1a2e"

    def test_save_chart_figure(self) -> None:
        """Test saves chart and returns path."""
        saver = ChartSaver(dpi=100.0, background_color="white")
        mock_fig = MagicMock()
        mock_tempfile = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/chart.png"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp
        mock_plt = MagicMock()

        result = saver.save_chart_figure(mock_fig, mock_tempfile, mock_plt)

        assert result == "/tmp/chart.png"
        mock_plt.savefig.assert_called_once_with(
            "/tmp/chart.png",
            dpi=100.0,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        mock_plt.close.assert_called_once_with(mock_fig)

    def test_save_chart_handles_close_error(self) -> None:
        """Test handles error during figure close."""
        saver = ChartSaver(dpi=100.0, background_color="white")
        mock_fig = MagicMock()
        mock_tempfile = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/chart.png"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp
        mock_plt = MagicMock()
        mock_plt.close.side_effect = RuntimeError("Close failed")

        result = saver.save_chart_figure(mock_fig, mock_tempfile, mock_plt)

        assert result == "/tmp/chart.png"
