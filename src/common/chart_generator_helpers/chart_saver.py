from __future__ import annotations

"""Helper for saving matplotlib charts to files"""


import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

logger = logging.getLogger("src.monitor.chart_generator")


class ChartSaver:
    """Saves matplotlib charts to temporary files"""

    def __init__(self, *, dpi: float, background_color: str):
        self.dpi = dpi
        self.background_color = background_color

    def save_chart_figure(self, fig: Figure, tempfile, plt) -> str:
        """Save chart figure to temporary file and return path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        try:
            plt.savefig(
                temp_file.name,
                dpi=self.dpi,
                bbox_inches="tight",
                facecolor=self.background_color,
                edgecolor="none",
            )
            return temp_file.name
        finally:
            try:
                plt.close(fig)
            except (RuntimeError, OSError, IOError) as cleanup_error:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
                logger.warning("Error during figure cleanup after save: %s", cleanup_error)
