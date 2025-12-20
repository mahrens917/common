from __future__ import annotations

"""Helper for annotating latest values on charts"""


import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from matplotlib.axes import Axes

logger = logging.getLogger("src.monitor.chart_generator")


class LatestValueAnnotator:
    """Annotates the latest value on charts"""

    def __init__(self, *, primary_color: str, highlight_color: Optional[str] = None):
        self.primary_color = primary_color
        self.highlight_color = highlight_color or primary_color

    def annotate_latest_value(
        self,
        *,
        ax: Axes,
        timestamp: datetime,
        value: float,
        formatter: Optional[Callable[[float], str]],
        mdates,
    ) -> None:
        """Annotate the latest value point on the chart"""
        numeric_timestamp = mdates.date2num(timestamp)
        ax.plot(
            [numeric_timestamp],
            [value],
            marker="o",
            markersize=8,
            color=self.highlight_color,
            zorder=5,
        )
        label = formatter(value) if formatter else f"{value:.2f}"
        ax.text(
            numeric_timestamp,
            value,
            label,
            fontsize=10,
            verticalalignment="bottom",
            horizontalalignment="left",
        )
