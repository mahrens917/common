"""Tests for pnl_breakdown_chart_renderer module."""

from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.pnl_breakdown_chart_renderer import (
    PnlBreakdownChartRenderer,
    _get_bar_color,
    _get_text_alignment,
)


class TestGetBarColor:
    """Tests for _get_bar_color function."""

    def test_positive_value(self) -> None:
        """Test positive value returns green."""
        result = _get_bar_color(100.0)
        assert result == "#28a745"

    def test_zero_value(self) -> None:
        """Test zero value returns green."""
        result = _get_bar_color(0.0)
        assert result == "#28a745"

    def test_negative_value(self) -> None:
        """Test negative value returns red."""
        result = _get_bar_color(-100.0)
        assert result == "#dc3545"


class TestGetTextAlignment:
    """Tests for _get_text_alignment function."""

    def test_positive_value(self) -> None:
        """Test positive value returns bottom."""
        result = _get_text_alignment(100.0)
        assert result == "bottom"

    def test_zero_value(self) -> None:
        """Test zero value returns bottom."""
        result = _get_text_alignment(0.0)
        assert result == "bottom"

    def test_negative_value(self) -> None:
        """Test negative value returns top."""
        result = _get_text_alignment(-100.0)
        assert result == "top"


class TestPnlBreakdownChartRenderer:
    """Tests for PnlBreakdownChartRenderer class."""

    def test_init(self) -> None:
        """Test PnlBreakdownChartRenderer initialization."""
        renderer = PnlBreakdownChartRenderer(
            chart_width_inches=12.0,
            chart_height_inches=6.0,
            dpi=150.0,
        )

        assert renderer.chart_width_inches == 12.0
        assert renderer.chart_height_inches == 6.0
        assert renderer.dpi == 150.0

    def test_generate_breakdown_chart_empty_data(self) -> None:
        """Test raises error when data is empty."""
        renderer = PnlBreakdownChartRenderer(
            chart_width_inches=12.0,
            chart_height_inches=6.0,
            dpi=150.0,
        )

        with pytest.raises(InsufficientDataError, match="No station breakdown data"):
            renderer.generate_breakdown_chart(
                data={},
                title="Test Chart",
                xlabel="Station",
                filename_suffix="test.png",
                np=MagicMock(),
                plt=MagicMock(),
                tempfile=MagicMock(),
            )

    def test_generate_breakdown_chart_success(self) -> None:
        """Test successful chart generation."""
        renderer = PnlBreakdownChartRenderer(
            chart_width_inches=12.0,
            chart_height_inches=6.0,
            dpi=150.0,
        )

        mock_np = MagicMock()
        mock_np.array.return_value = MagicMock()
        mock_np.array.return_value.__iter__ = lambda self: iter([1.0, -0.5])
        mock_np.array.return_value.__len__ = lambda self: 2

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        mock_bar1 = MagicMock()
        mock_bar1.get_x.return_value = 0
        mock_bar1.get_width.return_value = 1
        mock_bar1.get_height.return_value = 1.0
        mock_bar2 = MagicMock()
        mock_bar2.get_x.return_value = 1
        mock_bar2.get_width.return_value = 1
        mock_bar2.get_height.return_value = -0.5
        mock_ax.bar.return_value = [mock_bar1, mock_bar2]
        mock_ax.get_xticklabels.return_value = []

        mock_tempfile = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/chart.png"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp

        result = renderer.generate_breakdown_chart(
            data={"KJFK": 100, "KORD": -50},
            title="Station PnL",
            xlabel="Station",
            filename_suffix="test.png",
            np=mock_np,
            plt=mock_plt,
            tempfile=mock_tempfile,
        )

        assert result == "/tmp/chart.png"
        mock_plt.subplots.assert_called_once()
        mock_plt.savefig.assert_called_once()
        mock_plt.close.assert_called_once_with(mock_fig)

    def test_generate_breakdown_chart_with_many_labels(self) -> None:
        """Test chart generation with many labels rotates x-axis labels."""
        renderer = PnlBreakdownChartRenderer(
            chart_width_inches=12.0,
            chart_height_inches=6.0,
            dpi=150.0,
        )

        mock_np = MagicMock()
        values = [1.0] * 6
        mock_np.array.return_value = MagicMock()
        mock_np.array.return_value.__iter__ = lambda self: iter(values)
        mock_np.array.return_value.__len__ = lambda self: 6

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)

        mock_bars = [MagicMock() for _ in range(6)]
        for i, bar in enumerate(mock_bars):
            bar.get_x.return_value = i
            bar.get_width.return_value = 1
            bar.get_height.return_value = 1.0
        mock_ax.bar.return_value = mock_bars

        mock_label = MagicMock()
        mock_ax.get_xticklabels.return_value = [mock_label]

        mock_tempfile = MagicMock()
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/chart.png"
        mock_tempfile.NamedTemporaryFile.return_value = mock_temp

        data = {f"STA{i}": 100 for i in range(6)}
        renderer.generate_breakdown_chart(
            data=data,
            title="Station PnL",
            xlabel="Station",
            filename_suffix="test.png",
            np=mock_np,
            plt=mock_plt,
            tempfile=mock_tempfile,
        )

        mock_label.set_rotation.assert_called_once_with(45)
        mock_label.set_ha.assert_called_once_with("right")
