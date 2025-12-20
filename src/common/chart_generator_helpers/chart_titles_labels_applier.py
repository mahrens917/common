from __future__ import annotations

"""Helper for applying titles and labels to charts"""


import logging
from typing import TYPE_CHECKING

from .config import ChartTitlesLabelsData

if TYPE_CHECKING:
    pass

logger = logging.getLogger("src.monitor.chart_generator")


class ChartTitlesLabelsApplier:
    """Applies titles and axis labels to charts"""

    def apply_titles_and_labels(
        self,
        *,
        data: ChartTitlesLabelsData,
    ) -> None:
        """Apply title and axis labels with chart-specific formatting"""
        data.ax.set_title(data.chart_title, fontsize=14, fontweight="bold", pad=20)
        data.ax.set_facecolor("white")

        if data.is_temperature_chart:
            data.ax.yaxis.tick_right()
            data.ax.yaxis.set_label_position("right")
            min_temp = int(data.stats.min_value)
            max_temp = int(data.stats.max_value)
            if min_temp <= max_temp:
                temp_ticks = list(range(min_temp, max_temp + 1))
                data.ax.set_yticks(temp_ticks)
                data.ax.set_yticklabels([f"{temp}°F" for temp in temp_ticks])
            data.ax.set_xlabel("Timestamp")
        elif data.is_pnl_chart:
            data.ax.set_xlabel("Day")
            data.ax.set_ylabel("PnL")
        else:
            data.ax.set_xlabel("Timestamp")
            if data.y_label:
                data.ax.set_ylabel(data.y_label, fontsize=12)
