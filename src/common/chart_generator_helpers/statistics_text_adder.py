from __future__ import annotations

"""Helper for adding statistics text boxes to charts"""


import logging
from typing import TYPE_CHECKING, Callable, List, Optional

from common.chart_generator.contexts import ChartStatistics

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger("src.monitor.chart_generator")


class StatisticsTextAdder:
    """Adds statistics text boxes to charts"""

    def add_statistics_text(
        self,
        *,
        ax: Axes,
        stats: ChartStatistics,
        values: List[float],
        value_formatter: Optional[Callable[[float], str]],
        is_price_chart: bool,
        is_temperature_chart: bool,
        is_pnl_chart: bool,
    ) -> None:
        """Add statistics text box with formatted values"""
        if is_price_chart or is_temperature_chart:
            return

        if is_pnl_chart:
            total_pnl = sum(values)
            avg_pnl = stats.mean_value
            total_label = value_formatter(total_pnl) if value_formatter else f"{total_pnl:.2f}"
            average_label = value_formatter(avg_pnl) if value_formatter else f"{avg_pnl:.2f}"
            stats_text = f"Total: {total_label}\nAverage: {average_label}"
        else:
            min_label = value_formatter(stats.min_value) if value_formatter else f"{stats.min_value:.0f}"
            mean_label = value_formatter(stats.mean_value) if value_formatter else f"{stats.mean_value:.0f}"
            max_label = value_formatter(stats.max_value) if value_formatter else f"{stats.max_value:.0f}"
            stats_text = f"Min: {min_label}\nMean: {mean_label}\nMax: {max_label}"

        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )
