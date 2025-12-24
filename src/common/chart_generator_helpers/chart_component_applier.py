from __future__ import annotations

"""Helper for applying chart components (axes, titles, statistics)"""


import logging
from typing import TYPE_CHECKING

from common.chart_components import add_dawn_dusk_shading, add_vertical_line_annotations

from .axes_limits_configurator import AxesLimitsConfigurator
from .chart_titles_labels_applier import ChartTitlesLabelsApplier
from .config import (
    AxesLimitsConfig,
    ChartComponentData,
    ChartTitlesLabelsData,
    StatisticsFormattingConfig,
)
from .statistics_text_adder import StatisticsTextAdder

if TYPE_CHECKING:

    pass

logger = logging.getLogger("src.monitor.chart_generator")


class ChartComponentApplier:
    """Applies various chart components (axes, titles, statistics)"""

    def apply_chart_components(
        self,
        *,
        data: ChartComponentData,
    ) -> None:
        """Apply all chart components"""
        ax = data.ax
        values = data.values
        add_vertical_line_annotations(
            ax,
            data.vertical_lines,
            is_temperature_chart=data.is_temperature_chart,
            local_timezone=data.time_context.local_timezone,
        )

        if data.is_temperature_chart:
            add_dawn_dusk_shading(ax, data.dawn_dusk_periods, data.time_context.plot)

        limits_configurator = AxesLimitsConfigurator()
        limits_config = AxesLimitsConfig(
            ax=ax,
            values=values,
            stats=data.stats,
            time_context=data.time_context,
            overlay_result=data.overlay_result,
            prediction_values=data.prediction_values,
            prediction_uncertainties=data.prediction_uncertainties,
            is_pnl_chart=data.is_pnl_chart,
            is_price_chart=data.is_price_chart,
            is_temperature_chart=data.is_temperature_chart,
            kalshi_strikes=data.kalshi_strikes,
            mdates=data.mdates,
        )
        limits_configurator.configure_axes_limits_and_baselines(
            ax=ax,
            values=values,
            config=limits_config,
        )

        if data.is_temperature_chart and data.kalshi_strikes:
            data.add_kalshi_strike_lines_func(ax, data.kalshi_strikes)
            data.add_comprehensive_temperature_labels_func(ax, limits_configurator, data.kalshi_strikes)

        titles_applier = ChartTitlesLabelsApplier()
        titles_data = ChartTitlesLabelsData(
            ax=ax,
            chart_title=data.chart_title,
            y_label=data.y_label,
            stats=data.stats,
            time_context=data.time_context,
            is_temperature_chart=data.is_temperature_chart,
            is_pnl_chart=data.is_pnl_chart,
            station_icao=data.station_icao,
        )
        titles_applier.apply_titles_and_labels(data=titles_data)

    def apply_statistics_and_formatting(
        self,
        *,
        config: StatisticsFormattingConfig,
    ) -> None:
        """Apply statistics text and axis formatting"""
        stats_text_adder = StatisticsTextAdder()
        stats_text_adder.add_statistics_text(
            ax=config.ax,
            stats=config.stats,
            values=config.values,
            value_formatter=config.value_formatter,
            is_price_chart=config.is_price_chart,
            is_temperature_chart=config.is_temperature_chart,
            is_pnl_chart=config.is_pnl_chart,
        )

        config.format_y_axis_func(ax=config.ax, formatter=config.value_formatter)
