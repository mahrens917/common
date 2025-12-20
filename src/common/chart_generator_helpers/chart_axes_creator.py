from __future__ import annotations

"""Helper for creating and cleaning up matplotlib chart axes"""


import logging
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

logger = logging.getLogger("src.monitor.chart_generator")


class ChartAxesCreator:
    """Creates and cleans up matplotlib figure and axes"""

    def __init__(
        self,
        *,
        chart_width_inches: float,
        chart_height_inches: float,
        dpi: float,
        background_color: str,
    ):
        self.chart_width_inches = chart_width_inches
        self.chart_height_inches = chart_height_inches
        self.dpi = dpi
        self.background_color = background_color

    def create_chart_axes(self, plt) -> Tuple[Figure, Axes]:
        """Create new figure and axes with configured styling"""
        return plt.subplots(
            figsize=(self.chart_width_inches, self.chart_height_inches),
            dpi=self.dpi,
            facecolor=self.background_color,
        )

    def cleanup_chart_figure(self, fig, plt) -> None:
        """Clean up matplotlib figure resources"""
        try:
            plt.close(fig)
        except (RuntimeError, ValueError, TypeError) as cleanup_error:
            logger.warning("Error during matplotlib figure cleanup: %s", cleanup_error)
        try:
            plt.clf()
            plt.cla()
        except (RuntimeError, ValueError, TypeError) as cleanup_error:
            logger.warning("Error during matplotlib state cleanup: %s", cleanup_error)
