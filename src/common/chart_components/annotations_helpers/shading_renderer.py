"""Render nighttime shading on charts."""

import logging
from datetime import datetime
from typing import Callable, List, Tuple

logger = logging.getLogger(__name__)


def _create_shading_function(ax, label_applied_ref: List[bool]) -> Callable[[float, float], None]:
    """Create a closure for shading chart regions."""

    def shade(start: float, end: float) -> None:
        ax.axvspan(
            float(start),
            float(end),
            alpha=0.15,
            color="gray",
            label="Night Hours" if not label_applied_ref[0] else None,
            zorder=1,
        )
        label_applied_ref[0] = True

    return shade


def render_nighttime_shading(
    ax,
    all_dawns: List[Tuple[float, datetime]],
    all_dusks: List[Tuple[float, datetime]],
    chart_start: float,
    chart_end: float,
) -> None:
    """
    Render nighttime shading regions on chart.

    Args:
        ax: Matplotlib axis
        all_dawns: List of (numeric_time, datetime) for dawns
        all_dusks: List of (numeric_time, datetime) for dusks
        chart_start: Chart start time in matplotlib numeric format
        chart_end: Chart end time in matplotlib numeric format
    """
    label_applied_ref = [False]
    shade = _create_shading_function(ax, label_applied_ref)

    if all_dawns and all_dawns[0][0] > chart_start:
        shade(chart_start, all_dawns[0][0])
        logger.debug(
            "  Shaded from chart start to first dawn (%s)",
            all_dawns[0][1].strftime("%H:%M"),
        )

    for dusk_x, dusk_time in all_dusks:
        next_dawn = next((dawn for dawn in all_dawns if dawn[0] > dusk_x), None)
        if next_dawn:
            shade(dusk_x, next_dawn[0])
            logger.debug(
                "  Shaded dusk(%s) to dawn(%s)",
                dusk_time.strftime("%H:%M"),
                next_dawn[1].strftime("%H:%M"),
            )
        elif dusk_x < chart_end:
            shade(dusk_x, chart_end)
            logger.debug(
                "  Shaded dusk(%s) to chart end",
                dusk_time.strftime("%H:%M"),
            )
