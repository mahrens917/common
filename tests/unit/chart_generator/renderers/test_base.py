"""Tests for chart_generator.renderers.base module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator.renderers.base import (
    UnifiedChartAxisMixin,
    UnifiedChartHelperMixin,
    UnifiedChartParams,
    UnifiedChartRendererMixin,
    UnifiedChartStrikeMixin,
)

# Test constants for data_guard compliance
TEST_TIMESTAMP_1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
TEST_TIMESTAMP_2 = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
TEST_TIMESTAMP_3 = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
TEST_VALUE_1 = 100.0
TEST_VALUE_2 = 200.0
TEST_VALUE_3 = 150.0
TEST_CHART_TITLE = "Test Chart Title"
TEST_Y_LABEL = "Test Y Label"
TEST_STRIKE_TEMP_1 = 32.0
TEST_STRIKE_TEMP_2 = 50.0
TEST_STRIKE_TEMP_3 = 75.0
TEST_CHART_WIDTH = 12.0
TEST_CHART_HEIGHT = 6.0
TEST_DPI = 100.0
TEST_BACKGROUND_COLOR = "#1a1a2e"
TEST_PRIMARY_COLOR = "#00ff41"
TEST_SECONDARY_COLOR = "#ff6b6b"
TEST_HIGHLIGHT_COLOR = "#ffd700"
TEST_LINE_COLOR = "blue"
TEST_STATION_ICAO = "KJFK"
TEST_LATITUDE = 40.6413
TEST_LONGITUDE = -73.7781
TEST_TEMP_MIN = 30
TEST_TEMP_MAX = 80
TEST_FILE_PATH = "/tmp/test_chart.png"
TEST_PREDICTION_UNCERTAINTY = 5.0


class TestUnifiedChartParams:
    """Tests for UnifiedChartParams dataclass."""

    def test_init_with_required_fields(self) -> None:
        """Test initialization with required fields only."""
        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1],
            values=[TEST_VALUE_1],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        assert params.timestamps == [TEST_TIMESTAMP_1]
        assert params.values == [TEST_VALUE_1]
        assert params.chart_title == TEST_CHART_TITLE
        assert params.y_label == TEST_Y_LABEL
        assert params.value_formatter_func is None
        assert params.is_price_chart is False

    def test_init_with_all_fields(self) -> None:
        """Test initialization with all fields."""
        formatter = MagicMock()
        vertical_lines = [(TEST_TIMESTAMP_1, "label", "color")]
        dawn_dusk = [(TEST_TIMESTAMP_1, TEST_TIMESTAMP_2)]
        coords = (TEST_LATITUDE, TEST_LONGITUDE)

        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1, TEST_TIMESTAMP_2],
            values=[TEST_VALUE_1, TEST_VALUE_2],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
            value_formatter_func=formatter,
            is_price_chart=True,
            prediction_timestamps=[TEST_TIMESTAMP_3],
            prediction_values=[TEST_VALUE_3],
            prediction_uncertainties=[TEST_PREDICTION_UNCERTAINTY],
            vertical_lines=vertical_lines,
            is_temperature_chart=True,
            dawn_dusk_periods=dawn_dusk,
            station_coordinates=coords,
            is_pnl_chart=True,
            line_color=TEST_LINE_COLOR,
            kalshi_strikes=[TEST_STRIKE_TEMP_1, TEST_STRIKE_TEMP_2],
            station_icao=TEST_STATION_ICAO,
        )

        assert params.value_formatter_func is formatter
        assert params.is_price_chart is True
        assert params.station_icao == TEST_STATION_ICAO

    def test_frozen_dataclass(self) -> None:
        """Test that dataclass is frozen and immutable."""
        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1],
            values=[TEST_VALUE_1],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        with pytest.raises(AttributeError):
            params.chart_title = "New Title"  # type: ignore


class TestUnifiedChartHelperMixin:
    """Tests for UnifiedChartHelperMixin class."""

    def test_resolve_trade_visualizer_class_with_attribute(self) -> None:
        """Test resolves trade_visualizer_cls from instance attribute."""
        mock_cls = MagicMock()
        mixin = UnifiedChartHelperMixin()
        mixin.trade_visualizer_cls = mock_cls  # type: ignore

        result = mixin._resolve_trade_visualizer_class()

        assert result is mock_cls

    def test_resolve_trade_visualizer_class_from_module(self) -> None:
        """Test resolves TradeVisualizer from module when attribute not present."""
        mixin = UnifiedChartHelperMixin()
        mock_module = MagicMock()
        mock_trade_visualizer = MagicMock()
        mock_module.TradeVisualizer = mock_trade_visualizer

        with patch("common.chart_generator.renderers.base.import_module", return_value=mock_module):
            result = mixin._resolve_trade_visualizer_class()

        assert result is mock_trade_visualizer


class TestUnifiedChartStrikeMixin:
    """Tests for UnifiedChartStrikeMixin class."""

    def test_add_kalshi_strike_lines_single(self) -> None:
        """Test adds single Kalshi strike line."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()

        mixin._add_kalshi_strike_lines(mock_ax, [TEST_STRIKE_TEMP_1])

        mock_ax.axhline.assert_called_once_with(
            y=TEST_STRIKE_TEMP_1,
            color="grey",
            linestyle="-",
            linewidth=1.5,
            alpha=0.8,
            zorder=10,
        )

    def test_add_kalshi_strike_lines_multiple(self) -> None:
        """Test adds multiple Kalshi strike lines."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()
        strikes = [TEST_STRIKE_TEMP_1, TEST_STRIKE_TEMP_2, TEST_STRIKE_TEMP_3]

        mixin._add_kalshi_strike_lines(mock_ax, strikes)

        assert mock_ax.axhline.call_count == 3

    def test_add_comprehensive_temperature_labels_with_bounds_and_strikes(self) -> None:
        """Test adds temperature labels with explicit bounds and strikes."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()
        strikes = [TEST_STRIKE_TEMP_1, TEST_STRIKE_TEMP_2]

        mixin._add_comprehensive_temperature_labels(
            mock_ax,
            TEST_TEMP_MIN,
            TEST_TEMP_MAX,
            strikes,
        )

        mock_ax.set_yticks.assert_called_once()
        mock_ax.set_yticklabels.assert_called_once()

    def test_add_comprehensive_temperature_labels_with_bounds_no_strikes(self) -> None:
        """Test adds temperature labels with explicit bounds and no strikes."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()

        mixin._add_comprehensive_temperature_labels(
            mock_ax,
            TEST_TEMP_MIN,
            TEST_TEMP_MAX,
        )

        mock_ax.set_yticks.assert_called_once()

    def test_add_comprehensive_temperature_labels_from_axes_no_strikes(self) -> None:
        """Test adds temperature labels from axes limits without strikes."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()
        mock_ax.get_ylim.return_value = (TEST_TEMP_MIN + 0.3, TEST_TEMP_MAX - 0.7)

        mixin._add_comprehensive_temperature_labels(mock_ax, None)

        mock_ax.get_ylim.assert_called_once()
        mock_ax.set_yticks.assert_called_once()
        mock_ax.set_yticklabels.assert_called_once()

    def test_add_comprehensive_temperature_labels_from_axes_with_strikes(self) -> None:
        """Test adds temperature labels from axes limits with strikes."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()
        mock_ax.get_ylim.return_value = (TEST_TEMP_MIN + 0.5, TEST_TEMP_MAX - 0.5)
        strikes = [TEST_STRIKE_TEMP_1]
        # Create mock labels for the range
        mock_labels = [MagicMock() for _ in range(51)]  # 30 to 80 inclusive
        mock_ax.get_yticklabels.return_value = mock_labels

        mixin._add_comprehensive_temperature_labels(
            mock_ax,
            None,
            strikes,
        )

        mock_ax.get_ylim.assert_called_once()
        # Verify strike at index 2 (temp 32) is highlighted
        mock_labels[2].set_weight.assert_called_once_with("bold")
        mock_labels[2].set_color.assert_called_once_with("grey")

    def test_add_comprehensive_temperature_labels_highlights_strikes(self) -> None:
        """Test highlights strike temperatures in bold grey."""
        mixin = UnifiedChartStrikeMixin()
        mock_ax = MagicMock()
        # Range from 32 to 50 inclusive is 19 values
        mock_labels = [MagicMock() for _ in range(19)]
        mock_ax.get_yticklabels.return_value = mock_labels

        mixin._add_comprehensive_temperature_labels(
            mock_ax,
            32,
            50,
            [32.0, 50.0],
        )

        # First label (index 0, temp 32) should be bold and grey
        mock_labels[0].set_weight.assert_called_once_with("bold")
        mock_labels[0].set_color.assert_called_once_with("grey")
        # Last label (index 18, temp 50) should be bold and grey
        mock_labels[18].set_weight.assert_called_once_with("bold")
        mock_labels[18].set_color.assert_called_once_with("grey")


class TestUnifiedChartAxisMixin:
    """Tests for UnifiedChartAxisMixin class."""

    def test_format_y_axis_with_formatter(self) -> None:
        """Test formats y-axis with provided formatter."""
        mixin = UnifiedChartAxisMixin()
        mock_ax = MagicMock()
        mock_formatter = MagicMock(return_value="formatted")

        mixin._format_y_axis(mock_ax, mock_formatter)

        mock_ax.yaxis.set_major_formatter.assert_called_once()

    def test_format_y_axis_without_formatter(self) -> None:
        """Test does not format y-axis when formatter is None."""
        mixin = UnifiedChartAxisMixin()
        mock_ax = MagicMock()

        mixin._format_y_axis(mock_ax, None)

        mock_ax.yaxis.set_major_formatter.assert_not_called()


class TestUnifiedChartRendererMixin:
    """Tests for UnifiedChartRendererMixin class."""

    def _create_mock_renderer_instance(self) -> UnifiedChartRendererMixin:
        """Create mock renderer instance with required attributes."""
        instance = UnifiedChartRendererMixin()
        instance.chart_width_inches = TEST_CHART_WIDTH  # type: ignore
        instance.chart_height_inches = TEST_CHART_HEIGHT  # type: ignore
        instance.dpi = TEST_DPI  # type: ignore
        instance.background_color = TEST_BACKGROUND_COLOR  # type: ignore
        instance.primary_color = TEST_PRIMARY_COLOR  # type: ignore
        instance.secondary_color = TEST_SECONDARY_COLOR  # type: ignore
        instance.highlight_color = TEST_HIGHLIGHT_COLOR  # type: ignore
        instance._configure_time_axis = MagicMock()  # type: ignore
        return instance

    @pytest.mark.asyncio
    async def test_generate_unified_chart_with_params_object(self) -> None:
        """Test generates chart with UnifiedChartParams object."""
        instance = self._create_mock_renderer_instance()
        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1, TEST_TIMESTAMP_2],
            values=[TEST_VALUE_1, TEST_VALUE_2],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()

        with patch("common.chart_generator.renderers.base.ChartAxesCreator") as mock_creator_cls:
            mock_creator = MagicMock()
            mock_creator.create_chart_axes.return_value = (mock_fig, mock_ax)
            mock_creator_cls.return_value = mock_creator

            with patch("common.chart_generator.renderers.base.UnifiedChartRenderer") as mock_renderer_cls:
                mock_renderer = MagicMock()
                mock_renderer.render_chart_and_save = AsyncMock(return_value=TEST_FILE_PATH)
                mock_renderer_cls.return_value = mock_renderer

                with patch("common.chart_generator.renderers.base.plt", mock_plt):
                    result = await instance._generate_unified_chart(params=params)

                    assert result == TEST_FILE_PATH
                    mock_creator.cleanup_chart_figure.assert_called_once_with(mock_fig, mock_plt)

    @pytest.mark.asyncio
    async def test_generate_unified_chart_raises_on_empty_timestamps(self) -> None:
        """Test raises InsufficientDataError when timestamps are empty."""
        instance = self._create_mock_renderer_instance()
        params = UnifiedChartParams(
            timestamps=[],
            values=[TEST_VALUE_1],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        with pytest.raises(InsufficientDataError, match="No data provided for chart generation"):
            await instance._generate_unified_chart(params=params)

    @pytest.mark.asyncio
    async def test_generate_unified_chart_raises_on_empty_values(self) -> None:
        """Test raises InsufficientDataError when values are empty."""
        instance = self._create_mock_renderer_instance()
        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1],
            values=[],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        with pytest.raises(InsufficientDataError, match="No data provided for chart generation"):
            await instance._generate_unified_chart(params=params)

    @pytest.mark.asyncio
    async def test_generate_unified_chart_cleans_up_on_error(self) -> None:
        """Test cleans up figure even when render fails."""
        instance = self._create_mock_renderer_instance()
        params = UnifiedChartParams(
            timestamps=[TEST_TIMESTAMP_1],
            values=[TEST_VALUE_1],
            chart_title=TEST_CHART_TITLE,
            y_label=TEST_Y_LABEL,
        )

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()

        with patch("common.chart_generator.renderers.base.ChartAxesCreator") as mock_creator_cls:
            mock_creator = MagicMock()
            mock_creator.create_chart_axes.return_value = (mock_fig, mock_ax)
            mock_creator_cls.return_value = mock_creator

            with patch("common.chart_generator.renderers.base.UnifiedChartRenderer") as mock_renderer_cls:
                mock_renderer = MagicMock()
                mock_renderer.render_chart_and_save = AsyncMock(side_effect=RuntimeError("Render failed"))
                mock_renderer_cls.return_value = mock_renderer

                with patch("common.chart_generator.renderers.base.plt", mock_plt):
                    with pytest.raises(RuntimeError, match="Render failed"):
                        await instance._generate_unified_chart(params=params)

                    mock_creator.cleanup_chart_figure.assert_called_once_with(mock_fig, mock_plt)

    @pytest.mark.asyncio
    async def test_generate_unified_chart_public_method(self) -> None:
        """Test public generate_unified_chart method delegates correctly."""
        instance = self._create_mock_renderer_instance()

        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt = MagicMock()
        formatter = MagicMock()

        with patch("common.chart_generator.renderers.base.ChartAxesCreator") as mock_creator_cls:
            mock_creator = MagicMock()
            mock_creator.create_chart_axes.return_value = (mock_fig, mock_ax)
            mock_creator_cls.return_value = mock_creator

            with patch("common.chart_generator.renderers.base.UnifiedChartRenderer") as mock_renderer_cls:
                mock_renderer = MagicMock()
                mock_renderer.render_chart_and_save = AsyncMock(return_value=TEST_FILE_PATH)
                mock_renderer_cls.return_value = mock_renderer

                with patch("common.chart_generator.renderers.base.plt", mock_plt):
                    result = await instance.generate_unified_chart(
                        timestamps=[TEST_TIMESTAMP_1],
                        values=[TEST_VALUE_1],
                        chart_title=TEST_CHART_TITLE,
                        y_label=TEST_Y_LABEL,
                        value_formatter_func=formatter,
                        is_price_chart=True,
                    )

                    assert result == TEST_FILE_PATH

    def test_configure_time_axis_raises_not_implemented(self) -> None:
        """Test _configure_time_axis raises NotImplementedError."""
        # Create instance without mocking _configure_time_axis
        instance = UnifiedChartRendererMixin()
        instance.chart_width_inches = TEST_CHART_WIDTH  # type: ignore
        instance.chart_height_inches = TEST_CHART_HEIGHT  # type: ignore
        instance.dpi = TEST_DPI  # type: ignore
        instance.background_color = TEST_BACKGROUND_COLOR  # type: ignore
        instance.primary_color = TEST_PRIMARY_COLOR  # type: ignore
        instance.secondary_color = TEST_SECONDARY_COLOR  # type: ignore
        instance.highlight_color = TEST_HIGHLIGHT_COLOR  # type: ignore
        # Don't mock _configure_time_axis so it raises NotImplementedError

        mock_ax = MagicMock()

        with pytest.raises(
            NotImplementedError,
            match="_configure_time_axis must be provided by the renderer inheriting this mixin",
        ):
            instance._configure_time_axis(mock_ax, [TEST_TIMESTAMP_1])
