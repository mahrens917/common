from __future__ import annotations

"""Helper for rendering primary data series on charts"""


import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Tuple

from .config import PrimarySeriesRenderConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger("src.monitor.chart_generator")


class PrimarySeriesRenderer:
    """Renders the primary data series on charts"""

    def __init__(self, *, primary_color: str, secondary_color: str):
        self.primary_color = primary_color
        self.secondary_color = secondary_color

    def render_primary_series(
        self,
        *,
        config: PrimarySeriesRenderConfig,
    ) -> Optional[Tuple[datetime, float]]:
        """Render primary data series with appropriate styling"""
        if config.is_pnl_chart:
            x_values = list(range(len(config.values)))
            bar_colors = ["green" if value >= 0 else "red" for value in config.values]
            config.ax.bar(x_values, config.values, color=bar_colors, alpha=0.7, width=0.8)
            return None

        timestamps_numeric = config.mdates.date2num(config.time_context.plot)
        if config.is_temperature_chart:
            config.ax.fill_between(
                timestamps_numeric,
                config.values,
                alpha=0.3,
                color=config.plot_color,
                zorder=3,
                step="post",
            )
            config.ax.step(
                timestamps_numeric,
                config.values,
                where="post",
                color=config.plot_color,
                linewidth=2,
                zorder=4,
            )
        else:
            config.ax.fill_between(
                timestamps_numeric,
                config.values,
                alpha=0.3,
                color=config.plot_color,
                zorder=3,
            )
            config.ax.plot(
                timestamps_numeric,
                config.values,
                color=config.plot_color,
                linewidth=2,
                zorder=4,
            )

        latest_timestamp = config.time_context.plot[-1]
        latest_value = float(config.values[-1])

        if not config.is_price_chart and not config.is_temperature_chart:
            config.ax.axhline(
                y=float(config.stats.mean_value),
                color=self.secondary_color,
                linestyle="--",
                linewidth=1.2,
                alpha=0.8,
            )

        return latest_timestamp, latest_value
