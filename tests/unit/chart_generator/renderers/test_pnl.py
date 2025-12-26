"""Tests for chart_generator.renderers.pnl module."""

import asyncio
import os
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator.renderers.pnl import (
    PnlChartRendererMixin,
    _cleanup_partial_charts,
    _generate_cumulative_pnl_chart_impl,
    _generate_daily_pnl_chart_impl,
    _generate_rule_breakdown_chart_impl,
    _generate_station_breakdown_chart_impl,
    _render_chart,
)

# Module-level test constants
TEST_CHART_WIDTH = 12.0
TEST_CHART_HEIGHT = 6.0
TEST_DPI = 150.0
TEST_BACKGROUND_COLOR = "white"
TEST_PRIMARY_COLOR = "blue"
TEST_SECONDARY_COLOR = "gray"
TEST_HIGHLIGHT_COLOR = "red"
TEST_CHART_PATH = "/tmp/test_chart.png"
TEST_DATE_2024_01_01 = date(2024, 1, 1)
TEST_DATE_2024_01_02 = date(2024, 1, 2)
TEST_DATE_2024_01_03 = date(2024, 1, 3)
TEST_PNL_VALUE_100 = 100.0
TEST_PNL_VALUE_50 = 50.0
TEST_PNL_VALUE_NEG_25 = -25.0
TEST_STATION_KJFK = "KJFK"
TEST_STATION_KORD = "KORD"
TEST_RULE_MAX = "MAX"
TEST_RULE_MIN = "MIN"


class MockPnlChartRenderer:
    """Mock implementation of PnlChartRendererMixin for testing."""

    def __init__(self):
        self.chart_width_inches = TEST_CHART_WIDTH
        self.chart_height_inches = TEST_CHART_HEIGHT
        self.dpi = TEST_DPI
        self.background_color = TEST_BACKGROUND_COLOR
        self.primary_color = TEST_PRIMARY_COLOR
        self.secondary_color = TEST_SECONDARY_COLOR
        self.highlight_color = TEST_HIGHLIGHT_COLOR
        self.generate_unified_chart = AsyncMock(return_value=TEST_CHART_PATH)
        self._generate_daily_pnl_chart = AsyncMock(return_value=TEST_CHART_PATH)
        self._generate_cumulative_pnl_chart = AsyncMock(return_value=TEST_CHART_PATH)
        self._generate_station_breakdown_chart = MagicMock(return_value=TEST_CHART_PATH)
        self._generate_rule_breakdown_chart = MagicMock(return_value=TEST_CHART_PATH)


class TestPnlChartRendererMixinGeneratePnlCharts:
    """Tests for generate_pnl_charts method."""

    @pytest.mark.asyncio
    async def test_delegates_to_implementation(self) -> None:
        """Test delegates to _generate_pnl_charts_impl."""
        mixin = PnlChartRendererMixin()
        pnl_data = {"daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]}

        with patch.object(mixin, "_generate_pnl_charts_impl", new_callable=AsyncMock) as mock_impl:
            mock_impl.return_value = [TEST_CHART_PATH]

            result = await mixin.generate_pnl_charts(pnl_data)

            assert result == [TEST_CHART_PATH]
            mock_impl.assert_called_once_with(pnl_data)


class TestPnlChartRendererMixinGeneratePnlChartsImpl:
    """Tests for _generate_pnl_charts_impl method."""

    @pytest.mark.asyncio
    async def test_raises_error_when_empty_pnl_data(self) -> None:
        """Test raises InsufficientDataError when pnl_data is empty."""
        mixin = PnlChartRendererMixin()

        with pytest.raises(InsufficientDataError, match="No P&L data available for chart generation"):
            await mixin._generate_pnl_charts_impl({})

    @pytest.mark.asyncio
    async def test_generates_daily_pnl_chart_when_data_present(self) -> None:
        """Test generates daily P&L chart when daily_pnl data is present."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value=TEST_CHART_PATH)
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {"daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]}

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert result == [TEST_CHART_PATH]
        mixin._generate_daily_pnl_chart.assert_called_once_with([(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)])

    @pytest.mark.asyncio
    async def test_generates_cumulative_pnl_chart_when_data_present(self) -> None:
        """Test generates cumulative P&L chart when daily_pnl_dollars data is present."""
        mixin = MockPnlChartRenderer()
        mixin._generate_cumulative_pnl_chart = AsyncMock(return_value=TEST_CHART_PATH)
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {"daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]}

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert result == [TEST_CHART_PATH]
        mixin._generate_cumulative_pnl_chart.assert_called_once_with([(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)])

    @pytest.mark.asyncio
    async def test_generates_station_breakdown_chart_when_data_present(self) -> None:
        """Test generates station breakdown chart when station_breakdown data is present."""
        mixin = MockPnlChartRenderer()
        mixin._generate_station_breakdown_chart = MagicMock(return_value=TEST_CHART_PATH)
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {"station_breakdown": {TEST_STATION_KJFK: 100}}

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert result == [TEST_CHART_PATH]
        mixin._generate_station_breakdown_chart.assert_called_once_with({TEST_STATION_KJFK: 100})

    @pytest.mark.asyncio
    async def test_generates_rule_breakdown_chart_when_data_present(self) -> None:
        """Test generates rule breakdown chart when rule_breakdown data is present."""
        mixin = MockPnlChartRenderer()
        mixin._generate_rule_breakdown_chart = MagicMock(return_value=TEST_CHART_PATH)
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {"rule_breakdown": {TEST_RULE_MAX: 100}}

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert result == [TEST_CHART_PATH]
        mixin._generate_rule_breakdown_chart.assert_called_once_with({TEST_RULE_MAX: 100})

    @pytest.mark.asyncio
    async def test_skips_chart_when_data_missing(self) -> None:
        """Test skips chart generation when dataset is missing."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value=TEST_CHART_PATH)
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {"daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)], "daily_pnl_dollars": None}

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert result == [TEST_CHART_PATH]
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_generates_multiple_charts(self) -> None:
        """Test generates multiple charts when multiple datasets present."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(return_value="/tmp/cumulative.png")
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        result = await mixin._generate_pnl_charts_impl(pnl_data)

        assert len(result) == 2
        assert "/tmp/daily.png" in result
        assert "/tmp/cumulative.png" in result

    @pytest.mark.asyncio
    async def test_cleans_up_on_cancelled_error(self) -> None:
        """Test cleans up partial charts on CancelledError."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(side_effect=asyncio.CancelledError())
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        with patch("common.chart_generator.renderers.pnl._cleanup_partial_charts") as mock_cleanup:
            with pytest.raises(asyncio.CancelledError):
                await mixin._generate_pnl_charts_impl(pnl_data)

            mock_cleanup.assert_called_once_with(["/tmp/daily.png"])

    @pytest.mark.asyncio
    async def test_cleans_up_on_io_error(self) -> None:
        """Test cleans up partial charts on IOError."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(side_effect=IOError("Disk full"))
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        with patch("common.chart_generator.renderers.pnl._cleanup_partial_charts") as mock_cleanup:
            with pytest.raises(IOError, match="Disk full"):
                await mixin._generate_pnl_charts_impl(pnl_data)

            mock_cleanup.assert_called_once_with(["/tmp/daily.png"])

    @pytest.mark.asyncio
    async def test_cleans_up_on_os_error(self) -> None:
        """Test cleans up partial charts on OSError."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(side_effect=OSError("Permission denied"))
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        with patch("common.chart_generator.renderers.pnl._cleanup_partial_charts") as mock_cleanup:
            with pytest.raises(OSError, match="Permission denied"):
                await mixin._generate_pnl_charts_impl(pnl_data)

            mock_cleanup.assert_called_once_with(["/tmp/daily.png"])

    @pytest.mark.asyncio
    async def test_cleans_up_on_value_error(self) -> None:
        """Test cleans up partial charts on ValueError."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(side_effect=ValueError("Invalid data"))
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        with patch("common.chart_generator.renderers.pnl._cleanup_partial_charts") as mock_cleanup:
            with pytest.raises(ValueError, match="Invalid data"):
                await mixin._generate_pnl_charts_impl(pnl_data)

            mock_cleanup.assert_called_once_with(["/tmp/daily.png"])

    @pytest.mark.asyncio
    async def test_cleans_up_on_runtime_error(self) -> None:
        """Test cleans up partial charts on RuntimeError."""
        mixin = MockPnlChartRenderer()
        mixin._generate_daily_pnl_chart = AsyncMock(return_value="/tmp/daily.png")
        mixin._generate_cumulative_pnl_chart = AsyncMock(side_effect=RuntimeError("Failed"))
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
            "daily_pnl_dollars": [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)],
        }

        with patch("common.chart_generator.renderers.pnl._cleanup_partial_charts") as mock_cleanup:
            with pytest.raises(RuntimeError, match="Failed"):
                await mixin._generate_pnl_charts_impl(pnl_data)

            mock_cleanup.assert_called_once_with(["/tmp/daily.png"])

    @pytest.mark.asyncio
    async def test_raises_error_when_no_valid_data(self) -> None:
        """Test raises InsufficientDataError when no valid data for any chart."""
        mixin = MockPnlChartRenderer()
        mixin._generate_pnl_charts_impl = PnlChartRendererMixin._generate_pnl_charts_impl.__get__(mixin)

        pnl_data = {
            "daily_pnl": None,
            "daily_pnl_dollars": None,
            "station_breakdown": None,
            "rule_breakdown": None,
        }

        with pytest.raises(InsufficientDataError, match="No valid P&L data available for any chart type"):
            await mixin._generate_pnl_charts_impl(pnl_data)


class TestPnlChartRendererMixinGenerateDailyPnlChart:
    """Tests for _generate_daily_pnl_chart method."""

    @pytest.mark.asyncio
    async def test_delegates_to_implementation(self) -> None:
        """Test delegates to _generate_daily_pnl_chart_impl."""
        mixin = PnlChartRendererMixin()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch(
            "common.chart_generator.renderers.pnl._generate_daily_pnl_chart_impl",
            new_callable=AsyncMock,
        ) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin._generate_daily_pnl_chart(daily_pnl_data)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once_with(mixin, daily_pnl_data)


class TestPnlChartRendererMixinGenerateCumulativePnlChart:
    """Tests for _generate_cumulative_pnl_chart method."""

    @pytest.mark.asyncio
    async def test_delegates_to_implementation(self) -> None:
        """Test delegates to _generate_cumulative_pnl_chart_impl."""
        mixin = PnlChartRendererMixin()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch(
            "common.chart_generator.renderers.pnl._generate_cumulative_pnl_chart_impl",
            new_callable=AsyncMock,
        ) as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = await mixin._generate_cumulative_pnl_chart(daily_pnl_dollars)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once_with(mixin, daily_pnl_dollars)


class TestPnlChartRendererMixinGenerateStationBreakdownChart:
    """Tests for _generate_station_breakdown_chart method."""

    def test_delegates_to_implementation(self) -> None:
        """Test delegates to _generate_station_breakdown_chart_impl."""
        mixin = PnlChartRendererMixin()
        station_breakdown = {TEST_STATION_KJFK: 100}

        with patch("common.chart_generator.renderers.pnl._generate_station_breakdown_chart_impl") as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = mixin._generate_station_breakdown_chart(station_breakdown)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once_with(mixin, station_breakdown)


class TestPnlChartRendererMixinGenerateRuleBreakdownChart:
    """Tests for _generate_rule_breakdown_chart method."""

    def test_delegates_to_implementation(self) -> None:
        """Test delegates to _generate_rule_breakdown_chart_impl."""
        mixin = PnlChartRendererMixin()
        rule_breakdown = {TEST_RULE_MAX: 100}

        with patch("common.chart_generator.renderers.pnl._generate_rule_breakdown_chart_impl") as mock_impl:
            mock_impl.return_value = TEST_CHART_PATH

            result = mixin._generate_rule_breakdown_chart(rule_breakdown)

            assert result == TEST_CHART_PATH
            mock_impl.assert_called_once_with(mixin, rule_breakdown)


class TestGenerateDailyPnlChartImpl:
    """Tests for _generate_daily_pnl_chart_impl function."""

    @pytest.mark.asyncio
    async def test_raises_error_when_empty_data(self) -> None:
        """Test raises InsufficientDataError when data is empty."""
        mixin = MockPnlChartRenderer()

        with pytest.raises(InsufficientDataError, match="No daily P&L data available"):
            await _generate_daily_pnl_chart_impl(mixin, [])

    @pytest.mark.asyncio
    async def test_converts_dates_to_timestamps(self) -> None:
        """Test converts dates to datetime timestamps with UTC timezone."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [
            (TEST_DATE_2024_01_01, TEST_PNL_VALUE_100),
            (TEST_DATE_2024_01_02, TEST_PNL_VALUE_50),
        ]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        timestamps = call_args.kwargs["timestamps"]

        assert len(timestamps) == 2
        assert timestamps[0] == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert timestamps[1] == datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_extracts_values_as_floats(self) -> None:
        """Test extracts P&L values as floats."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [
            (TEST_DATE_2024_01_01, TEST_PNL_VALUE_100),
            (TEST_DATE_2024_01_02, TEST_PNL_VALUE_50),
        ]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        values = call_args.kwargs["values"]

        assert values == [TEST_PNL_VALUE_100, TEST_PNL_VALUE_50]
        assert all(isinstance(v, float) for v in values)

    @pytest.mark.asyncio
    async def test_sets_chart_title(self) -> None:
        """Test sets correct chart title."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        assert call_args.kwargs["chart_title"] == "Daily P&L (Percentage)"

    @pytest.mark.asyncio
    async def test_sets_empty_y_label(self) -> None:
        """Test sets empty y-axis label."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        assert call_args.kwargs["y_label"] == ""

    @pytest.mark.asyncio
    async def test_sets_percentage_formatter(self) -> None:
        """Test sets value formatter for percentage display."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        formatter = call_args.kwargs["value_formatter_func"]

        assert formatter(TEST_PNL_VALUE_100) == "+100.00%"
        assert formatter(TEST_PNL_VALUE_NEG_25) == "-25.00%"

    @pytest.mark.asyncio
    async def test_sets_is_pnl_chart_flag(self) -> None:
        """Test sets is_pnl_chart flag to True."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        call_args = mixin.generate_unified_chart.call_args
        assert call_args.kwargs["is_pnl_chart"] is True

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns path from generate_unified_chart."""
        mixin = MockPnlChartRenderer()
        daily_pnl_data = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        result = await _generate_daily_pnl_chart_impl(mixin, daily_pnl_data)

        assert result == TEST_CHART_PATH


class TestGenerateCumulativePnlChartImpl:
    """Tests for _generate_cumulative_pnl_chart_impl function."""

    @pytest.mark.asyncio
    async def test_raises_error_when_empty_data(self) -> None:
        """Test raises InsufficientDataError when data is empty."""
        mixin = MockPnlChartRenderer()

        with pytest.raises(InsufficientDataError, match="No cumulative P&L data available"):
            await _generate_cumulative_pnl_chart_impl(mixin, [])

    @pytest.mark.asyncio
    async def test_converts_dates_to_timestamps(self) -> None:
        """Test converts dates to datetime timestamps with UTC timezone."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [
            (TEST_DATE_2024_01_01, TEST_PNL_VALUE_100),
            (TEST_DATE_2024_01_02, TEST_PNL_VALUE_50),
        ]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0, 1.5])
            mock_np.cumsum.return_value = mock_cumsum_result

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            call_args = mixin.generate_unified_chart.call_args
            timestamps = call_args.kwargs["timestamps"]

            assert len(timestamps) == 2
            assert timestamps[0] == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            assert timestamps[1] == datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_calculates_cumulative_sum(self) -> None:
        """Test calculates cumulative sum of P&L dollars."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [
            (TEST_DATE_2024_01_01, TEST_PNL_VALUE_100),
            (TEST_DATE_2024_01_02, TEST_PNL_VALUE_50),
            (TEST_DATE_2024_01_03, TEST_PNL_VALUE_NEG_25),
        ]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum = MagicMock()
            mock_cumsum.__truediv__ = MagicMock(return_value=[1.0, 1.5, 1.25])
            mock_np.cumsum.return_value = mock_cumsum

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            mock_np.cumsum.assert_called_once()
            call_args = mock_np.cumsum.call_args[0][0]
            assert call_args == [TEST_PNL_VALUE_100, TEST_PNL_VALUE_50, TEST_PNL_VALUE_NEG_25]

    @pytest.mark.asyncio
    async def test_converts_cents_to_dollars(self) -> None:
        """Test converts cumulative cents to dollars by dividing by 100."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, 10050.0)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum = MagicMock()
            mock_cumsum.__truediv__ = MagicMock(return_value=[100.5])
            mock_np.cumsum.return_value = mock_cumsum

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            mock_cumsum.__truediv__.assert_called_once_with(100.0)

    @pytest.mark.asyncio
    async def test_sets_chart_title(self) -> None:
        """Test sets correct chart title."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0])
            mock_np.cumsum.return_value = mock_cumsum_result

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            call_args = mixin.generate_unified_chart.call_args
            assert call_args.kwargs["chart_title"] == "Cumulative P&L (Dollars)"

    @pytest.mark.asyncio
    async def test_sets_empty_y_label(self) -> None:
        """Test sets empty y-axis label."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0])
            mock_np.cumsum.return_value = mock_cumsum_result

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            call_args = mixin.generate_unified_chart.call_args
            assert call_args.kwargs["y_label"] == ""

    @pytest.mark.asyncio
    async def test_sets_dollar_formatter(self) -> None:
        """Test sets value formatter for dollar display."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0])
            mock_np.cumsum.return_value = mock_cumsum_result

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            call_args = mixin.generate_unified_chart.call_args
            formatter = call_args.kwargs["value_formatter_func"]

            assert formatter(TEST_PNL_VALUE_100) == "$+100.00"
            assert formatter(TEST_PNL_VALUE_NEG_25) == "$-25.00"

    @pytest.mark.asyncio
    async def test_sets_is_pnl_chart_flag(self) -> None:
        """Test sets is_pnl_chart flag to True."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0])
            mock_np.cumsum.return_value = mock_cumsum_result

            await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            call_args = mixin.generate_unified_chart.call_args
            assert call_args.kwargs["is_pnl_chart"] is True

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns path from generate_unified_chart."""
        mixin = MockPnlChartRenderer()
        daily_pnl_dollars = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        with patch("common.chart_generator.renderers.pnl.np") as mock_np:
            mock_cumsum_result = MagicMock()
            mock_cumsum_result.__truediv__ = MagicMock(return_value=[1.0])
            mock_np.cumsum.return_value = mock_cumsum_result

            result = await _generate_cumulative_pnl_chart_impl(mixin, daily_pnl_dollars)

            assert result == TEST_CHART_PATH


class TestGenerateStationBreakdownChartImpl:
    """Tests for _generate_station_breakdown_chart_impl function."""

    def test_creates_pnl_breakdown_renderer_with_attributes(self) -> None:
        """Test creates PnlBreakdownChartRenderer with mixin attributes."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            with patch("common.chart_generator.renderers.pnl.np"):
                with patch("common.chart_generator.renderers.pnl.plt"):
                    with patch("common.chart_generator.renderers.pnl.tempfile"):
                        _generate_station_breakdown_chart_impl(mixin, {TEST_STATION_KJFK: 100})

                        mock_renderer_class.assert_called_once_with(
                            chart_width_inches=TEST_CHART_WIDTH,
                            chart_height_inches=TEST_CHART_HEIGHT,
                            dpi=TEST_DPI,
                        )

    def test_calls_generate_breakdown_chart_with_station_config(self) -> None:
        """Test calls generate_breakdown_chart with station configuration."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            mock_np = MagicMock()
            mock_plt = MagicMock()
            mock_tempfile = MagicMock()

            with patch("common.chart_generator.renderers.pnl.np", mock_np):
                with patch("common.chart_generator.renderers.pnl.plt", mock_plt):
                    with patch("common.chart_generator.renderers.pnl.tempfile", mock_tempfile):
                        station_data = {TEST_STATION_KJFK: 100, TEST_STATION_KORD: 50}
                        _generate_station_breakdown_chart_impl(mixin, station_data)

                        mock_renderer.generate_breakdown_chart.assert_called_once_with(
                            data=station_data,
                            title="Station P&L Breakdown",
                            xlabel="Station",
                            filename_suffix="station.png",
                            np=mock_np,
                            plt=mock_plt,
                            tempfile=mock_tempfile,
                        )

    def test_returns_chart_path(self) -> None:
        """Test returns chart path from renderer."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            with patch("common.chart_generator.renderers.pnl.np"):
                with patch("common.chart_generator.renderers.pnl.plt"):
                    with patch("common.chart_generator.renderers.pnl.tempfile"):
                        result = _generate_station_breakdown_chart_impl(mixin, {TEST_STATION_KJFK: 100})

                        assert result == TEST_CHART_PATH


class TestGenerateRuleBreakdownChartImpl:
    """Tests for _generate_rule_breakdown_chart_impl function."""

    def test_creates_pnl_breakdown_renderer_with_attributes(self) -> None:
        """Test creates PnlBreakdownChartRenderer with mixin attributes."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            with patch("common.chart_generator.renderers.pnl.np"):
                with patch("common.chart_generator.renderers.pnl.plt"):
                    with patch("common.chart_generator.renderers.pnl.tempfile"):
                        _generate_rule_breakdown_chart_impl(mixin, {TEST_RULE_MAX: 100})

                        mock_renderer_class.assert_called_once_with(
                            chart_width_inches=TEST_CHART_WIDTH,
                            chart_height_inches=TEST_CHART_HEIGHT,
                            dpi=TEST_DPI,
                        )

    def test_calls_generate_breakdown_chart_with_rule_config(self) -> None:
        """Test calls generate_breakdown_chart with rule configuration."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            mock_np = MagicMock()
            mock_plt = MagicMock()
            mock_tempfile = MagicMock()

            with patch("common.chart_generator.renderers.pnl.np", mock_np):
                with patch("common.chart_generator.renderers.pnl.plt", mock_plt):
                    with patch("common.chart_generator.renderers.pnl.tempfile", mock_tempfile):
                        rule_data = {TEST_RULE_MAX: 100, TEST_RULE_MIN: 50}
                        _generate_rule_breakdown_chart_impl(mixin, rule_data)

                        mock_renderer.generate_breakdown_chart.assert_called_once_with(
                            data=rule_data,
                            title="Rule P&L Breakdown",
                            xlabel="Rule",
                            filename_suffix="rule.png",
                            np=mock_np,
                            plt=mock_plt,
                            tempfile=mock_tempfile,
                        )

    def test_returns_chart_path(self) -> None:
        """Test returns chart path from renderer."""
        mixin = MockPnlChartRenderer()

        with patch("common.chart_generator.renderers.pnl.PnlBreakdownChartRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.generate_breakdown_chart.return_value = TEST_CHART_PATH
            mock_renderer_class.return_value = mock_renderer

            with patch("common.chart_generator.renderers.pnl.np"):
                with patch("common.chart_generator.renderers.pnl.plt"):
                    with patch("common.chart_generator.renderers.pnl.tempfile"):
                        result = _generate_rule_breakdown_chart_impl(mixin, {TEST_RULE_MAX: 100})

                        assert result == TEST_CHART_PATH


class TestRenderChart:
    """Tests for _render_chart function."""

    @pytest.mark.asyncio
    async def test_calls_generator_with_dataset(self) -> None:
        """Test calls generator function with dataset."""
        mixin = MockPnlChartRenderer()
        mock_generator = MagicMock(return_value=TEST_CHART_PATH)
        dataset = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        result = await _render_chart(mixin, mock_generator, dataset)

        mock_generator.assert_called_once_with(dataset)
        assert result == TEST_CHART_PATH

    @pytest.mark.asyncio
    async def test_awaits_async_result(self) -> None:
        """Test awaits result when generator returns awaitable."""
        mixin = MockPnlChartRenderer()
        mock_generator = AsyncMock(return_value=TEST_CHART_PATH)
        dataset = [(TEST_DATE_2024_01_01, TEST_PNL_VALUE_100)]

        result = await _render_chart(mixin, mock_generator, dataset)

        assert result == TEST_CHART_PATH

    @pytest.mark.asyncio
    async def test_returns_sync_result_directly(self) -> None:
        """Test returns synchronous result directly without awaiting."""
        mixin = MockPnlChartRenderer()
        mock_generator = MagicMock(return_value=TEST_CHART_PATH)
        dataset = {TEST_STATION_KJFK: 100}

        result = await _render_chart(mixin, mock_generator, dataset)

        assert result == TEST_CHART_PATH


class TestCleanupPartialCharts:
    """Tests for _cleanup_partial_charts function."""

    def test_deletes_existing_files(self) -> None:
        """Test deletes files that exist."""
        chart_paths = ["/tmp/chart1.png", "/tmp/chart2.png"]

        with patch("common.chart_generator.renderers.pnl.os.path.exists") as mock_exists:
            with patch("common.chart_generator.renderers.pnl.os.unlink") as mock_unlink:
                mock_exists.side_effect = [True, True]

                _cleanup_partial_charts(chart_paths)

                assert mock_exists.call_count == 2
                assert mock_unlink.call_count == 2
                mock_unlink.assert_any_call("/tmp/chart1.png")
                mock_unlink.assert_any_call("/tmp/chart2.png")

    def test_skips_nonexistent_files(self) -> None:
        """Test skips files that do not exist."""
        chart_paths = ["/tmp/chart1.png", "/tmp/chart2.png"]

        with patch("common.chart_generator.renderers.pnl.os.path.exists") as mock_exists:
            with patch("common.chart_generator.renderers.pnl.os.unlink") as mock_unlink:
                mock_exists.side_effect = [True, False]

                _cleanup_partial_charts(chart_paths)

                assert mock_exists.call_count == 2
                mock_unlink.assert_called_once_with("/tmp/chart1.png")

    def test_continues_on_os_error(self) -> None:
        """Test continues cleanup even when deletion fails."""
        chart_paths = ["/tmp/chart1.png", "/tmp/chart2.png"]

        with patch("common.chart_generator.renderers.pnl.os.path.exists") as mock_exists:
            with patch("common.chart_generator.renderers.pnl.os.unlink") as mock_unlink:
                mock_exists.side_effect = [True, True]
                mock_unlink.side_effect = [OSError("Permission denied"), None]

                _cleanup_partial_charts(chart_paths)

                assert mock_unlink.call_count == 2

    def test_logs_warning_on_cleanup_failure(self) -> None:
        """Test logs warning when cleanup fails."""
        chart_paths = ["/tmp/chart1.png"]

        with patch("common.chart_generator.renderers.pnl.os.path.exists", return_value=True):
            with patch("common.chart_generator.renderers.pnl.os.unlink") as mock_unlink:
                with patch("common.chart_generator.renderers.pnl.logger") as mock_logger:
                    mock_unlink.side_effect = OSError("Permission denied")

                    _cleanup_partial_charts(chart_paths)

                    mock_logger.warning.assert_called_once_with("Unable to clean up P&L chart %s", "/tmp/chart1.png")

    def test_handles_empty_list(self) -> None:
        """Test handles empty chart paths list."""
        with patch("common.chart_generator.renderers.pnl.os.path.exists") as mock_exists:
            _cleanup_partial_charts([])

            mock_exists.assert_not_called()
