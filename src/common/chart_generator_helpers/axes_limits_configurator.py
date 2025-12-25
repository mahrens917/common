from __future__ import annotations

"""Helper for configuring axes limits and baselines"""


import logging
from typing import TYPE_CHECKING, List, Optional

from common.chart_components import collect_prediction_extrema
from common.chart_generator.contexts import ChartStatistics, ChartTimeContext

from .config import AxesLimitsConfig

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger("src.monitor.chart_generator")


class AxesLimitsConfigurator:
    """Configures axes limits and baselines for charts"""

    def configure_axes_limits_and_baselines(
        self: AxesLimitsConfigurator, *, ax: Axes, values: List[float], config: AxesLimitsConfig
    ) -> None:
        extended_values = list(values)
        extended_values.extend(
            collect_prediction_extrema(
                config.overlay_result,
                config.prediction_values,
                config.prediction_uncertainties,
            )
        )
        extended_min = min(extended_values)
        extended_max = max(extended_values)
        data_range = extended_max - extended_min
        if data_range > 0:
            padding_ratio = 0.15
            minimum_padding = max(abs(extended_max), abs(extended_min)) * 0.03
            y_axis_padding = max(data_range * padding_ratio, minimum_padding, 1.0)
        else:
            y_axis_padding = max(abs(extended_max) * 0.02, 1.0)
        ax.set_ylim(extended_min - y_axis_padding, extended_max + y_axis_padding)
        self._configure_x_limits(ax, values, config.time_context, config.is_pnl_chart, config.mdates)
        self._add_baseline_lines(
            ax,
            config.stats,
            config.is_pnl_chart,
            config.is_price_chart,
            config.is_temperature_chart,
            config.kalshi_strikes,
        )

    def _configure_x_limits(
        self: AxesLimitsConfigurator,
        ax: Axes,
        values: List[float],
        time_context: ChartTimeContext,
        is_pnl_chart: bool,
        mdates,
    ) -> None:
        if is_pnl_chart:
            if values:
                ax.set_xlim(-0.5, len(values) - 0.5)
            return
        timestamps_for_limits = list(time_context.plot)
        if time_context.prediction:
            timestamps_for_limits.extend(time_context.prediction)
        if timestamps_for_limits:
            start_time = mdates.date2num(min(timestamps_for_limits))
            end_time = mdates.date2num(max(timestamps_for_limits))
            time_range = end_time - start_time
            if time_range > 0:
                padding = time_range * 0.02
            else:
                padding = 0.01
            ax.set_xlim(float(start_time - padding), float(end_time + padding))

    def _add_baseline_lines(
        self: AxesLimitsConfigurator,
        ax: Axes,
        stats: ChartStatistics,
        is_pnl_chart: bool,
        is_price_chart: bool,
        is_temperature_chart: bool,
        kalshi_strikes: Optional[List[float]],
    ) -> None:
        if is_pnl_chart:
            ax.axhline(y=0, color="black", linestyle="-", alpha=0.5, linewidth=1)
        elif not is_price_chart and not is_temperature_chart:
            ax.axhline(y=float(stats.min_value), color="red", linestyle="--", alpha=0.7, linewidth=1)
            ax.axhline(y=float(stats.mean_value), color="red", linestyle="--", alpha=0.7, linewidth=1)
            ax.axhline(y=float(stats.max_value), color="red", linestyle="--", alpha=0.7, linewidth=1)
        if is_temperature_chart and kalshi_strikes:
            self._expand_for_strikes(ax, kalshi_strikes)

    def _expand_for_strikes(self: AxesLimitsConfigurator, ax: Axes, kalshi_strikes: List[float]) -> None:
        current_ylim = ax.get_ylim()
        min_strike = min(kalshi_strikes)
        max_strike = max(kalshi_strikes)
        new_ymin = min(current_ylim[0], min_strike - 2)
        new_ymax = max(current_ylim[1], max_strike + 2)
        ax.set_ylim(new_ymin, new_ymax)
        logger.info(
            "Expanded y-axis from %s to (%s, %s) to include Kalshi strikes",
            current_ylim,
            new_ymin,
            new_ymax,
        )
