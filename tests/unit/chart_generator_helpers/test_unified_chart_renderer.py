"""Tests for chart_generator_helpers.unified_chart_renderer module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator_helpers.unified_chart_renderer import UnifiedChartRenderer


class TestUnifiedChartRendererInit:
    """Tests for UnifiedChartRenderer initialization."""

    def test_stores_colors(self) -> None:
        """Test stores color configuration."""
        renderer = UnifiedChartRenderer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
            dpi=100.0,
            background_color="white",
            configure_time_axis_func=MagicMock(),
        )

        assert renderer.primary_color == "blue"
        assert renderer.secondary_color == "gray"
        assert renderer.highlight_color == "red"

    def test_stores_dpi(self) -> None:
        """Test stores dpi setting."""
        renderer = UnifiedChartRenderer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
            dpi=150.0,
            background_color="white",
            configure_time_axis_func=MagicMock(),
        )

        assert renderer.dpi == 150.0

    def test_stores_background_color(self) -> None:
        """Test stores background color."""
        renderer = UnifiedChartRenderer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
            dpi=100.0,
            background_color="#f0f0f0",
            configure_time_axis_func=MagicMock(),
        )

        assert renderer.background_color == "#f0f0f0"

    def test_stores_configure_func(self) -> None:
        """Test stores configure time axis function."""
        mock_func = MagicMock()

        renderer = UnifiedChartRenderer(
            primary_color="blue",
            secondary_color="gray",
            highlight_color="red",
            dpi=100.0,
            background_color="white",
            configure_time_axis_func=mock_func,
        )

        assert renderer.configure_time_axis_func is mock_func


class TestUnifiedChartRendererRenderChartAndSave:
    """Tests for render_chart_and_save method."""

    @pytest.mark.asyncio
    async def test_creates_data_preparer(self) -> None:
        """Test creates ChartDataPreparer with colors."""
        now = datetime.now(tz=timezone.utc)
        mock_fig = MagicMock()
        mock_ax = MagicMock()

        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartDataPreparer") as mock_preparer:
            mock_instance = MagicMock()
            mock_time_ctx = MagicMock()
            mock_stats = MagicMock()
            mock_instance.prepare_and_render_series.return_value = (mock_time_ctx, mock_stats, None, None)
            mock_preparer.return_value = mock_instance

            with patch("common.chart_generator_helpers.unified_chart_renderer.ChartPreparationData"):
                with patch("common.chart_generator_helpers.unified_chart_renderer.ChartComponentData"):
                    with patch("common.chart_generator_helpers.unified_chart_renderer.ChartFeaturesApplier") as mock_applier:
                        mock_applier.return_value.apply_all_features = AsyncMock()
                        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartSaver") as mock_saver:
                            mock_saver.return_value.save_chart_figure.return_value = "/path/chart.png"

                            renderer = UnifiedChartRenderer(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                                dpi=100.0,
                                background_color="white",
                                configure_time_axis_func=MagicMock(),
                            )

                            await renderer.render_chart_and_save(
                                fig=mock_fig,
                                ax=mock_ax,
                                timestamps=[now],
                                values=[50.0],
                                is_temperature_chart=False,
                                is_price_chart=False,
                                is_pnl_chart=False,
                                chart_title="Test",
                                y_label="Y",
                                mdates=MagicMock(),
                                np=MagicMock(),
                                tempfile=MagicMock(),
                                plt=MagicMock(),
                                format_y_axis_func=MagicMock(),
                                resolve_trade_visualizer_func=MagicMock(),
                                add_kalshi_strike_lines_func=MagicMock(),
                                add_comprehensive_temperature_labels_func=MagicMock(),
                            )

                            mock_preparer.assert_called_once_with(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                            )

    @pytest.mark.asyncio
    async def test_applies_features(self) -> None:
        """Test applies all features to chart."""
        now = datetime.now(tz=timezone.utc)
        mock_fig = MagicMock()
        mock_ax = MagicMock()

        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartDataPreparer") as mock_preparer:
            mock_instance = MagicMock()
            mock_time_ctx = MagicMock()
            mock_stats = MagicMock()
            mock_instance.prepare_and_render_series.return_value = (mock_time_ctx, mock_stats, None, None)
            mock_preparer.return_value = mock_instance

            with patch("common.chart_generator_helpers.unified_chart_renderer.ChartPreparationData"):
                with patch("common.chart_generator_helpers.unified_chart_renderer.ChartComponentData"):
                    with patch("common.chart_generator_helpers.unified_chart_renderer.ChartFeaturesApplier") as mock_applier:
                        mock_features = MagicMock()
                        mock_features.apply_all_features = AsyncMock()
                        mock_applier.return_value = mock_features

                        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartSaver") as mock_saver:
                            mock_saver.return_value.save_chart_figure.return_value = "/path/chart.png"

                            renderer = UnifiedChartRenderer(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                                dpi=100.0,
                                background_color="white",
                                configure_time_axis_func=MagicMock(),
                            )

                            await renderer.render_chart_and_save(
                                fig=mock_fig,
                                ax=mock_ax,
                                timestamps=[now],
                                values=[50.0],
                                is_temperature_chart=False,
                                is_price_chart=False,
                                is_pnl_chart=False,
                                chart_title="Test",
                                y_label="Y",
                                mdates=MagicMock(),
                                np=MagicMock(),
                                tempfile=MagicMock(),
                                plt=MagicMock(),
                                format_y_axis_func=MagicMock(),
                                resolve_trade_visualizer_func=MagicMock(),
                                add_kalshi_strike_lines_func=MagicMock(),
                                add_comprehensive_temperature_labels_func=MagicMock(),
                            )

                            mock_features.apply_all_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_chart(self) -> None:
        """Test saves chart figure."""
        now = datetime.now(tz=timezone.utc)
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_tempfile = MagicMock()
        mock_plt = MagicMock()

        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartDataPreparer") as mock_preparer:
            mock_instance = MagicMock()
            mock_instance.prepare_and_render_series.return_value = (MagicMock(), MagicMock(), None, None)
            mock_preparer.return_value = mock_instance

            with patch("common.chart_generator_helpers.unified_chart_renderer.ChartPreparationData"):
                with patch("common.chart_generator_helpers.unified_chart_renderer.ChartComponentData"):
                    with patch("common.chart_generator_helpers.unified_chart_renderer.ChartFeaturesApplier") as mock_applier:
                        mock_applier.return_value.apply_all_features = AsyncMock()

                        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartSaver") as mock_saver:
                            mock_saver_instance = MagicMock()
                            mock_saver_instance.save_chart_figure.return_value = "/output/chart.png"
                            mock_saver.return_value = mock_saver_instance

                            renderer = UnifiedChartRenderer(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                                dpi=150.0,
                                background_color="black",
                                configure_time_axis_func=MagicMock(),
                            )

                            await renderer.render_chart_and_save(
                                fig=mock_fig,
                                ax=mock_ax,
                                timestamps=[now],
                                values=[50.0],
                                is_temperature_chart=False,
                                is_price_chart=False,
                                is_pnl_chart=False,
                                chart_title="Test",
                                y_label="Y",
                                mdates=MagicMock(),
                                np=MagicMock(),
                                tempfile=mock_tempfile,
                                plt=mock_plt,
                                format_y_axis_func=MagicMock(),
                                resolve_trade_visualizer_func=MagicMock(),
                                add_kalshi_strike_lines_func=MagicMock(),
                                add_comprehensive_temperature_labels_func=MagicMock(),
                            )

                            mock_saver.assert_called_once_with(dpi=150.0, background_color="black")
                            mock_saver_instance.save_chart_figure.assert_called_once_with(mock_fig, mock_tempfile, mock_plt)

    @pytest.mark.asyncio
    async def test_returns_chart_path(self) -> None:
        """Test returns chart file path."""
        now = datetime.now(tz=timezone.utc)

        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartDataPreparer") as mock_preparer:
            mock_instance = MagicMock()
            mock_instance.prepare_and_render_series.return_value = (MagicMock(), MagicMock(), None, None)
            mock_preparer.return_value = mock_instance

            with patch("common.chart_generator_helpers.unified_chart_renderer.ChartPreparationData"):
                with patch("common.chart_generator_helpers.unified_chart_renderer.ChartComponentData"):
                    with patch("common.chart_generator_helpers.unified_chart_renderer.ChartFeaturesApplier") as mock_applier:
                        mock_applier.return_value.apply_all_features = AsyncMock()

                        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartSaver") as mock_saver:
                            mock_saver.return_value.save_chart_figure.return_value = "/final/path.png"

                            renderer = UnifiedChartRenderer(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                                dpi=100.0,
                                background_color="white",
                                configure_time_axis_func=MagicMock(),
                            )

                            result = await renderer.render_chart_and_save(
                                fig=MagicMock(),
                                ax=MagicMock(),
                                timestamps=[now],
                                values=[50.0],
                                is_temperature_chart=False,
                                is_price_chart=False,
                                is_pnl_chart=False,
                                chart_title="Test",
                                y_label="Y",
                                mdates=MagicMock(),
                                np=MagicMock(),
                                tempfile=MagicMock(),
                                plt=MagicMock(),
                                format_y_axis_func=MagicMock(),
                                resolve_trade_visualizer_func=MagicMock(),
                                add_kalshi_strike_lines_func=MagicMock(),
                                add_comprehensive_temperature_labels_func=MagicMock(),
                            )

                            assert result == "/final/path.png"

    @pytest.mark.asyncio
    async def test_calls_tight_layout(self) -> None:
        """Test calls tight_layout on figure."""
        now = datetime.now(tz=timezone.utc)
        mock_fig = MagicMock()

        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartDataPreparer") as mock_preparer:
            mock_instance = MagicMock()
            mock_instance.prepare_and_render_series.return_value = (MagicMock(), MagicMock(), None, None)
            mock_preparer.return_value = mock_instance

            with patch("common.chart_generator_helpers.unified_chart_renderer.ChartPreparationData"):
                with patch("common.chart_generator_helpers.unified_chart_renderer.ChartComponentData"):
                    with patch("common.chart_generator_helpers.unified_chart_renderer.ChartFeaturesApplier") as mock_applier:
                        mock_applier.return_value.apply_all_features = AsyncMock()

                        with patch("common.chart_generator_helpers.unified_chart_renderer.ChartSaver") as mock_saver:
                            mock_saver.return_value.save_chart_figure.return_value = "/path.png"

                            renderer = UnifiedChartRenderer(
                                primary_color="blue",
                                secondary_color="gray",
                                highlight_color="red",
                                dpi=100.0,
                                background_color="white",
                                configure_time_axis_func=MagicMock(),
                            )

                            await renderer.render_chart_and_save(
                                fig=mock_fig,
                                ax=MagicMock(),
                                timestamps=[now],
                                values=[50.0],
                                is_temperature_chart=False,
                                is_price_chart=False,
                                is_pnl_chart=False,
                                chart_title="Test",
                                y_label="Y",
                                mdates=MagicMock(),
                                np=MagicMock(),
                                tempfile=MagicMock(),
                                plt=MagicMock(),
                                format_y_axis_func=MagicMock(),
                                resolve_trade_visualizer_func=MagicMock(),
                                add_kalshi_strike_lines_func=MagicMock(),
                                add_comprehensive_temperature_labels_func=MagicMock(),
                            )

                            mock_fig.tight_layout.assert_called_once()
