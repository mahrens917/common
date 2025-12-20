from __future__ import annotations

"""Helper for applying all chart features"""


import logging
from typing import TYPE_CHECKING, List, Optional

from .chart_component_applier import ChartComponentApplier
from .config import ChartComponentData, StatisticsFormattingConfig

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger("src.monitor.chart_generator")


class ChartFeaturesApplier:
    """Applies all chart features including components, trades, and axes"""

    def __init__(self, *, configure_time_axis_func):
        self.configure_time_axis_func = configure_time_axis_func

    async def apply_all_features(
        self,
        *,
        data: ChartComponentData,
        format_y_axis_func,
        resolve_trade_visualizer_func,
        station_coordinates,
    ) -> None:
        """Apply all chart features"""
        component_applier = ChartComponentApplier()
        component_applier.apply_chart_components(data=data)

        await self._annotate_trades_if_required(
            ax=data.ax,
            station_icao=data.station_icao,
            time_context=data.time_context,
            is_temperature_chart=data.is_temperature_chart,
            kalshi_strikes=data.kalshi_strikes,
            resolve_trade_visualizer_func=resolve_trade_visualizer_func,
        )

        chart_type = "default"
        if data.is_temperature_chart:
            chart_type = "temperature"
        elif data.is_price_chart:
            chart_type = "price"
        elif data.is_pnl_chart:
            chart_type = "pnl"

        self.configure_time_axis_func(
            data.ax,
            data.time_context.plot,
            chart_type=chart_type,
            station_coordinates=station_coordinates,
        )

        stats_config = StatisticsFormattingConfig(
            ax=data.ax,
            stats=data.stats,
            values=data.values,
            value_formatter=data.value_formatter,
            is_price_chart=data.is_price_chart,
            is_temperature_chart=data.is_temperature_chart,
            is_pnl_chart=data.is_pnl_chart,
            format_y_axis_func=format_y_axis_func,
        )
        component_applier.apply_statistics_and_formatting(config=stats_config)

    async def _annotate_trades_if_required(
        self,
        *,
        ax: Axes,
        station_icao: Optional[str],
        time_context,
        is_temperature_chart: bool,
        kalshi_strikes: Optional[List[float]],
        resolve_trade_visualizer_func,
    ) -> None:
        """Annotate trades if required"""
        from src.common.chart_components import annotate_trades_if_needed

        trade_visualizer_cls = resolve_trade_visualizer_func()
        await annotate_trades_if_needed(
            ax=ax,
            station_icao=station_icao,
            naive_timestamps=time_context.naive,
            plot_timestamps=time_context.plot,
            is_temperature_chart=is_temperature_chart,
            kalshi_strikes=kalshi_strikes,
            trade_visualizer_cls=trade_visualizer_cls,
        )
