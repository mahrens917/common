"""Tests for axes_limits_configurator module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator.contexts import ChartStatistics, ChartTimeContext
from common.chart_generator_helpers.axes_limits_configurator import AxesLimitsConfigurator
from common.chart_generator_helpers.config import AxesLimitsConfig

# Test constants for chart statistics
TEST_CHART_MIN_VALUE = 10.0
TEST_CHART_MEAN_VALUE = 50.0
TEST_CHART_MAX_VALUE = 90.0


@pytest.fixture
def mock_ax() -> MagicMock:
    """Create a mock Axes object."""
    ax = MagicMock()
    ax.set_ylim = MagicMock()
    ax.set_xlim = MagicMock()
    ax.get_ylim = MagicMock(return_value=(0, 100))
    ax.axhline = MagicMock()
    return ax


@pytest.fixture
def mock_time_context() -> MagicMock:
    """Create a mock ChartTimeContext."""
    context = MagicMock(spec=ChartTimeContext)
    context.plot = [datetime(2024, 12, 25, 12, 0, tzinfo=timezone.utc)]
    context.prediction = None
    return context


@pytest.fixture
def mock_stats() -> MagicMock:
    """Create a mock ChartStatistics."""
    stats = MagicMock(spec=ChartStatistics)
    stats.min_value = TEST_CHART_MIN_VALUE
    stats.mean_value = TEST_CHART_MEAN_VALUE
    stats.max_value = TEST_CHART_MAX_VALUE
    return stats


@pytest.fixture
def mock_mdates() -> MagicMock:
    """Create a mock mdates module."""
    mdates = MagicMock()
    mdates.date2num = MagicMock(return_value=1.0)
    return mdates


class TestAxesLimitsConfigurator:
    """Tests for AxesLimitsConfigurator class."""

    def test_configure_axes_limits_and_baselines(
        self,
        mock_ax: MagicMock,
        mock_time_context: MagicMock,
        mock_stats: MagicMock,
        mock_mdates: MagicMock,
    ) -> None:
        """Test configuring axes limits and baselines."""
        configurator = AxesLimitsConfigurator()
        config = AxesLimitsConfig(
            ax=mock_ax,
            values=[10.0, 50.0, 90.0],
            time_context=mock_time_context,
            stats=mock_stats,
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=False,
            mdates=mock_mdates,
            overlay_result=None,
            prediction_values=None,
            prediction_uncertainties=None,
            kalshi_strikes=None,
        )

        with patch("common.chart_generator_helpers.axes_limits_configurator.collect_prediction_extrema", return_value=[]):
            configurator.configure_axes_limits_and_baselines(
                ax=mock_ax,
                values=[10.0, 50.0, 90.0],
                config=config,
            )

        mock_ax.set_ylim.assert_called_once()

    def test_configure_x_limits_pnl_chart(
        self,
        mock_ax: MagicMock,
        mock_time_context: MagicMock,
        mock_mdates: MagicMock,
    ) -> None:
        """Test x-axis limits for PnL chart."""
        configurator = AxesLimitsConfigurator()

        configurator._configure_x_limits(
            mock_ax,
            values=[1.0, 2.0, 3.0],
            time_context=mock_time_context,
            is_pnl_chart=True,
            mdates=mock_mdates,
        )

        mock_ax.set_xlim.assert_called_once_with(-0.5, 2.5)

    def test_configure_x_limits_pnl_chart_empty_values(
        self,
        mock_ax: MagicMock,
        mock_time_context: MagicMock,
        mock_mdates: MagicMock,
    ) -> None:
        """Test x-axis limits for PnL chart with empty values."""
        configurator = AxesLimitsConfigurator()

        configurator._configure_x_limits(
            mock_ax,
            values=[],
            time_context=mock_time_context,
            is_pnl_chart=True,
            mdates=mock_mdates,
        )

        mock_ax.set_xlim.assert_not_called()

    def test_configure_x_limits_time_chart(
        self,
        mock_ax: MagicMock,
        mock_time_context: MagicMock,
        mock_mdates: MagicMock,
    ) -> None:
        """Test x-axis limits for time-based chart."""
        mock_mdates.date2num.side_effect = [1.0, 2.0]
        mock_time_context.prediction = None
        configurator = AxesLimitsConfigurator()

        configurator._configure_x_limits(
            mock_ax,
            values=[10.0],
            time_context=mock_time_context,
            is_pnl_chart=False,
            mdates=mock_mdates,
        )

        mock_ax.set_xlim.assert_called_once()

    def test_add_baseline_lines_pnl_chart(
        self,
        mock_ax: MagicMock,
        mock_stats: MagicMock,
    ) -> None:
        """Test baseline lines for PnL chart."""
        configurator = AxesLimitsConfigurator()

        configurator._add_baseline_lines(
            mock_ax,
            stats=mock_stats,
            is_pnl_chart=True,
            is_price_chart=False,
            is_temperature_chart=False,
            kalshi_strikes=None,
        )

        mock_ax.axhline.assert_called_once()
        call_kwargs = mock_ax.axhline.call_args[1]
        assert call_kwargs["y"] == 0

    def test_add_baseline_lines_regular_chart(
        self,
        mock_ax: MagicMock,
        mock_stats: MagicMock,
    ) -> None:
        """Test baseline lines for regular chart."""
        configurator = AxesLimitsConfigurator()

        configurator._add_baseline_lines(
            mock_ax,
            stats=mock_stats,
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=False,
            kalshi_strikes=None,
        )

        assert mock_ax.axhline.call_count == 3

    def test_add_baseline_lines_price_chart(
        self,
        mock_ax: MagicMock,
        mock_stats: MagicMock,
    ) -> None:
        """Test baseline lines for price chart."""
        configurator = AxesLimitsConfigurator()

        configurator._add_baseline_lines(
            mock_ax,
            stats=mock_stats,
            is_pnl_chart=False,
            is_price_chart=True,
            is_temperature_chart=False,
            kalshi_strikes=None,
        )

        mock_ax.axhline.assert_not_called()

    def test_add_baseline_lines_temperature_chart_with_strikes(
        self,
        mock_ax: MagicMock,
        mock_stats: MagicMock,
    ) -> None:
        """Test baseline lines for temperature chart with strikes."""
        configurator = AxesLimitsConfigurator()

        configurator._add_baseline_lines(
            mock_ax,
            stats=mock_stats,
            is_pnl_chart=False,
            is_price_chart=False,
            is_temperature_chart=True,
            kalshi_strikes=[40.0, 50.0],
        )

        mock_ax.get_ylim.assert_called_once()
        mock_ax.set_ylim.assert_called_once()

    def test_expand_for_strikes(
        self,
        mock_ax: MagicMock,
    ) -> None:
        """Test expanding y-axis for strikes."""
        mock_ax.get_ylim.return_value = (45.0, 55.0)
        configurator = AxesLimitsConfigurator()

        configurator._expand_for_strikes(mock_ax, [40.0, 60.0])

        mock_ax.set_ylim.assert_called_once_with(38.0, 62.0)
