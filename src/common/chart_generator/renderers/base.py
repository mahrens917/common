from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Any, Callable, List, Optional, Tuple

from common.chart_generator_helpers.chart_axes_creator import ChartAxesCreator
from common.chart_generator_helpers.unified_chart_renderer import UnifiedChartRenderer

from ..dependencies import mdates, np, plt, tempfile, ticker
from ..exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")


@dataclass(frozen=True)
class UnifiedChartParams:
    """Parameters for unified chart generation."""

    timestamps: List[datetime]
    values: List[float]
    chart_title: str
    y_label: str
    value_formatter_func: Optional[Callable] = None
    is_price_chart: bool = False
    prediction_timestamps: Optional[List[datetime]] = None
    prediction_values: Optional[List[float]] = None
    prediction_uncertainties: Optional[List[float]] = None
    vertical_lines: Optional[List[Tuple[datetime, str, str]]] = None
    is_temperature_chart: bool = False
    dawn_dusk_periods: Optional[List[Tuple[datetime, datetime]]] = None
    station_coordinates: Optional[Tuple[float, float]] = None
    is_pnl_chart: bool = False
    line_color: Optional[str] = None
    kalshi_strikes: Optional[List[float]] = None
    station_icao: Optional[str] = None


class UnifiedChartHelperMixin:
    trade_visualizer_cls: Optional[Any] = None

    def _resolve_trade_visualizer_class(self) -> Any:
        if self.trade_visualizer_cls is not None:
            return self.trade_visualizer_cls
        trade_module = import_module("src.monitor.chart_generator")
        return trade_module.TradeVisualizer


class UnifiedChartStrikeMixin:
    def _add_kalshi_strike_lines(self, ax, kalshi_strikes: List[float]) -> None:
        logger.info("Adding %s Kalshi strike lines", len(kalshi_strikes))
        for strike_temp in kalshi_strikes:
            ax.axhline(
                y=strike_temp,
                color="grey",
                linestyle="-",
                linewidth=1.5,
                alpha=0.8,
                zorder=10,
            )

    def _add_comprehensive_temperature_labels(
        self,
        ax,
        bounds_or_config,
        maybe_second=None,
        maybe_third=None,
    ) -> None:
        import math

        strikes: List[float]
        if isinstance(bounds_or_config, (int, float)) and isinstance(maybe_second, (int, float)):
            temp_min = math.floor(bounds_or_config)
            temp_max = math.ceil(maybe_second)
            if maybe_third:
                strikes = list(maybe_third)
            else:
                strikes = []
        else:
            y_min, y_max = ax.get_ylim()
            temp_min = math.floor(y_min)
            temp_max = math.ceil(y_max)
            if maybe_second:
                strikes = list(maybe_second)
            else:
                strikes = []
        ticks = list(range(temp_min, temp_max + 1))
        ax.set_yticks(ticks)
        ax.set_yticklabels([f"{temp:d}°F" for temp in ticks])
        for index, temp in enumerate(ticks):
            if temp in strikes:
                tick_label = ax.get_yticklabels()[index]
                tick_label.set_weight("bold")
                tick_label.set_color("grey")


class UnifiedChartAxisMixin:
    def _format_y_axis(self, ax, formatter: Optional[Callable[[float], str]]) -> None:
        if formatter:
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: formatter(x)))


class UnifiedChartRendererMixin(
    UnifiedChartHelperMixin,
    UnifiedChartStrikeMixin,
    UnifiedChartAxisMixin,
):
    """Shared helpers for rendering unified monitor charts."""

    chart_width_inches: float
    chart_height_inches: float
    dpi: float
    background_color: str
    primary_color: str
    secondary_color: str
    highlight_color: str

    async def _generate_unified_chart(
        self: UnifiedChartRendererMixin,
        params: Optional[UnifiedChartParams] = None,
        **kwargs,
    ) -> str:
        # Build params from keyword arguments if not passed as UnifiedChartParams
        if params is None:
            from .unified_chart_params_builder import build_unified_chart_params

            params = build_unified_chart_params(**kwargs)
        if not params.timestamps or not params.values:
            raise InsufficientDataError("No data provided for chart generation")
        axes_creator = ChartAxesCreator(
            chart_width_inches=self.chart_width_inches,
            chart_height_inches=self.chart_height_inches,
            dpi=self.dpi,
            background_color=self.background_color,
        )

        fig, ax = axes_creator.create_chart_axes(plt)
        try:
            renderer = UnifiedChartRenderer(
                primary_color=self.primary_color,
                secondary_color=self.secondary_color,
                highlight_color=getattr(self, "highlight_color", self.primary_color),
                dpi=self.dpi,
                background_color=self.background_color,
                configure_time_axis_func=self._configure_time_axis,
            )
            return await renderer.render_chart_and_save(
                fig=fig,
                ax=ax,
                timestamps=params.timestamps,
                values=params.values,
                chart_title=params.chart_title,
                y_label=params.y_label,
                value_formatter=params.value_formatter_func,
                is_price_chart=params.is_price_chart,
                prediction_timestamps=params.prediction_timestamps,
                prediction_values=params.prediction_values,
                prediction_uncertainties=params.prediction_uncertainties,
                vertical_lines=params.vertical_lines,
                is_temperature_chart=params.is_temperature_chart,
                dawn_dusk_periods=params.dawn_dusk_periods,
                station_coordinates=params.station_coordinates,
                is_pnl_chart=params.is_pnl_chart,
                line_color=params.line_color,
                kalshi_strikes=params.kalshi_strikes,
                station_icao=params.station_icao,
                resolve_trade_visualizer_func=self._resolve_trade_visualizer_class,
                add_kalshi_strike_lines_func=self._add_kalshi_strike_lines,
                add_comprehensive_temperature_labels_func=self._add_comprehensive_temperature_labels,
                format_y_axis_func=self._format_y_axis,
                mdates=mdates,
                np=np,
                plt=plt,
                tempfile=tempfile,
                ticker=ticker,
            )
        finally:
            axes_creator.cleanup_chart_figure(fig, plt)

    async def generate_unified_chart(self, *, timestamps, values, chart_title: str, y_label: str, value_formatter_func, **kwargs) -> str:
        """Public helper that delegates to the private renderer implementation."""
        return await self._generate_unified_chart(
            timestamps=timestamps, values=values, chart_title=chart_title,
            y_label=y_label, value_formatter_func=value_formatter_func, **kwargs,
        )

    def _configure_time_axis(
        self,
        ax,
        timestamps,
        chart_type: str = "default",
        station_coordinates=None,
    ):
        raise NotImplementedError("_configure_time_axis must be provided by the renderer inheriting this mixin")
