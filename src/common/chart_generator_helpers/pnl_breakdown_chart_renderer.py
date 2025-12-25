from __future__ import annotations

"""Helper for rendering breakdown charts (station/rule PnL)"""


import logging
from typing import TYPE_CHECKING, Dict

from common.chart_generator.exceptions import InsufficientDataError

if TYPE_CHECKING:
    pass

logger = logging.getLogger("src.monitor.chart_generator")

# Threshold for rotating x-axis labels to prevent overlap
_MIN_LABELS_FOR_ROTATION = 5


def _get_bar_color(value: float) -> str:
    """Get color for bar based on value sign."""
    if value >= 0:
        return "#28a745"
    return "#dc3545"


def _get_text_alignment(value: float) -> str:
    """Get vertical alignment for text based on value sign."""
    if value >= 0:
        return "bottom"
    return "top"


class PnlBreakdownChartRenderer:
    """Renders breakdown bar charts for station and rule PnL"""

    def __init__(self, *, chart_width_inches: float, chart_height_inches: float, dpi: float):
        self.chart_width_inches = chart_width_inches
        self.chart_height_inches = chart_height_inches
        self.dpi = dpi

    def generate_breakdown_chart(
        self,
        *,
        data: Dict[str, int],
        title: str,
        xlabel: str,
        filename_suffix: str,
        np,
        plt,
        tempfile,
    ) -> str:
        """Generate a breakdown bar chart for PnL data"""
        if not data:
            raise InsufficientDataError(f"No {xlabel.lower()} breakdown data available")

        labels = list(data.keys())
        values = np.array(list(data.values()), dtype=float) / 100.0

        fig, ax = plt.subplots(figsize=(self.chart_width_inches, self.chart_height_inches), dpi=self.dpi)
        try:
            colors = [_get_bar_color(value) for value in values]
            bars = ax.bar(labels, values, color=colors)
            ax.set_title(title)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Total P&L ($)")
            ax.grid(axis="y", linestyle="--", alpha=0.5)

            for bar, value in zip(bars, values):
                va_value = _get_text_alignment(value)
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"${value:+.2f}",
                    ha="center",
                    va=va_value,
                )

            if len(labels) >= _MIN_LABELS_FOR_ROTATION:
                for label in ax.get_xticklabels():
                    label.set_rotation(45)
                    label.set_ha("right")

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename_suffix}")
            plt.savefig(temp_file.name, bbox_inches="tight")
            return temp_file.name
        finally:
            try:
                plt.close(fig)
            except (RuntimeError, ValueError, TypeError) as exc:  # pragma: no cover - log only  # policy_guard: allow-silent-handler
                logger.warning("Error during matplotlib figure cleanup: %s", exc)
