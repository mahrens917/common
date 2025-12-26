"""Tests for chart_generator_helpers.statistics_text_adder module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator.contexts import ChartStatistics
from common.chart_generator_helpers.statistics_text_adder import StatisticsTextAdder


class TestStatisticsTextAdderAddStatisticsText:
    """Tests for add_statistics_text method."""

    def test_skips_price_chart(self) -> None:
        """Test skips adding text for price chart."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[1, 2, 3],
            value_formatter=None,
            is_price_chart=True,
            is_temperature_chart=False,
            is_pnl_chart=False,
        )

        mock_ax.text.assert_not_called()

    def test_skips_temperature_chart(self) -> None:
        """Test skips adding text for temperature chart."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=0, max_value=100, mean_value=50)

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[1, 2, 3],
            value_formatter=None,
            is_price_chart=False,
            is_temperature_chart=True,
            is_pnl_chart=False,
        )

        mock_ax.text.assert_not_called()

    def test_adds_pnl_stats(self) -> None:
        """Test adds PnL statistics text."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=-10, max_value=30, mean_value=10)

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[10, 20, 30],
            value_formatter=None,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=True,
        )

        mock_ax.text.assert_called_once()
        call_args = mock_ax.text.call_args
        text = call_args[0][2]
        assert "Total:" in text
        assert "Average:" in text

    def test_adds_pnl_stats_with_formatter(self) -> None:
        """Test adds PnL statistics with formatter."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=-10, max_value=30, mean_value=10)

        def formatter(val: float) -> str:
            return f"${val:.2f}"

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[10, 20, 30],
            value_formatter=formatter,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=True,
        )

        call_args = mock_ax.text.call_args
        text = call_args[0][2]
        assert "$60.00" in text  # Total
        assert "$10.00" in text  # Average

    def test_adds_default_stats(self) -> None:
        """Test adds default min/mean/max statistics."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=10, max_value=100, mean_value=50)

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[10, 50, 100],
            value_formatter=None,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=False,
        )

        mock_ax.text.assert_called_once()
        call_args = mock_ax.text.call_args
        text = call_args[0][2]
        assert "Min:" in text
        assert "Mean:" in text
        assert "Max:" in text

    def test_adds_default_stats_with_formatter(self) -> None:
        """Test adds default stats with formatter."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=10, max_value=100, mean_value=50)

        def formatter(val: float) -> str:
            return f"{val}%"

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[10, 50, 100],
            value_formatter=formatter,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=False,
        )

        call_args = mock_ax.text.call_args
        text = call_args[0][2]
        assert "10%" in text
        assert "50%" in text
        assert "100%" in text

    def test_text_positioning(self) -> None:
        """Test text is positioned correctly."""
        adder = StatisticsTextAdder()
        mock_ax = MagicMock()
        stats = ChartStatistics(min_value=10, max_value=100, mean_value=50)

        adder.add_statistics_text(
            ax=mock_ax,
            stats=stats,
            values=[10, 50, 100],
            value_formatter=None,
            is_price_chart=False,
            is_temperature_chart=False,
            is_pnl_chart=False,
        )

        call_args = mock_ax.text.call_args
        assert call_args[0][0] == 0.02  # x position
        assert call_args[0][1] == 0.98  # y position
        assert call_args[1]["verticalalignment"] == "top"
