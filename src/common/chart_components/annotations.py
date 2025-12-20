from __future__ import annotations

import logging
from datetime import datetime, timezone, tzinfo
from typing import List, Optional, Sequence, Tuple

import matplotlib.dates as mdates

logger = logging.getLogger(__name__)


def add_dawn_dusk_shading(
    ax,
    dawn_dusk_periods: Optional[Sequence[Tuple[datetime, datetime]]],
    timestamps_for_shading: Optional[Sequence[datetime]],
) -> None:
    """
    Shade nighttime periods (from dusk to next dawn) on the chart.

    Args:
        ax: Matplotlib axis to annotate.
        dawn_dusk_periods: Sequence of (dawn, dusk) datetimes.
        timestamps_for_shading: Timestamps used for the plotted series.
    """
    if not dawn_dusk_periods or not timestamps_for_shading:
        return

    logger.info("🌅 Adding nighttime shading for %d dawn/dusk periods", len(dawn_dusk_periods))
    chart_start, chart_end = _chart_bounds(timestamps_for_shading)
    dawns, dusks = _build_sorted_dawn_dusk_lists(dawn_dusk_periods)

    shading = _NightShadingContext(ax)
    _shade_initial_gap(shading, dawns, chart_start)
    _shade_between_dusks_and_dawns(shading, dawns, dusks, chart_end)


def _chart_bounds(timestamps: Sequence[datetime]) -> Tuple[float, float]:
    series = list(timestamps)
    return (
        float(mdates.date2num(series[0])),
        float(mdates.date2num(series[-1])),
    )


def _build_sorted_dawn_dusk_lists(
    dawn_dusk_periods: Sequence[Tuple[datetime, datetime]],
) -> Tuple[List[Tuple[float, datetime]], List[Tuple[float, datetime]]]:
    dawns: List[Tuple[float, datetime]] = []
    dusks: List[Tuple[float, datetime]] = []
    for dawn, dusk in dawn_dusk_periods:
        dawns.append(_timestamp_with_naive_datetime(dawn))
        dusks.append(_timestamp_with_naive_datetime(dusk))

    dawns.sort(key=lambda entry: entry[0])
    dusks.sort(key=lambda entry: entry[0])
    logger.debug("  Found %d dawns and %d dusks", len(dawns), len(dusks))
    return dawns, dusks


def _timestamp_with_naive_datetime(moment: datetime) -> Tuple[float, datetime]:
    naive = moment.replace(tzinfo=None) if moment.tzinfo else moment
    return float(mdates.date2num(naive)), naive


class _NightShadingContext:
    def __init__(self, ax):
        self._ax = ax
        self._label_applied = False

    def shade(self, start: float, end: float) -> None:
        self._ax.axvspan(
            float(start),
            float(end),
            alpha=0.15,
            color="gray",
            label="Night Hours" if not self._label_applied else None,
            zorder=1,
        )
        self._label_applied = True


def _shade_initial_gap(
    shading: _NightShadingContext,
    dawns: Sequence[Tuple[float, datetime]],
    chart_start: float,
) -> None:
    if dawns and dawns[0][0] > chart_start:
        shading.shade(chart_start, dawns[0][0])
        logger.debug(
            "  Shaded from chart start to first dawn (%s)",
            dawns[0][1].strftime("%H:%M"),
        )


def _shade_between_dusks_and_dawns(
    shading: _NightShadingContext,
    dawns: Sequence[Tuple[float, datetime]],
    dusks: Sequence[Tuple[float, datetime]],
    chart_end: float,
) -> None:
    for dusk_x, dusk_time in dusks:
        next_dawn = _next_dawn_after(dawns, dusk_x)
        if next_dawn:
            shading.shade(dusk_x, next_dawn[0])
            logger.debug(
                "  Shaded dusk(%s) to dawn(%s)",
                dusk_time.strftime("%H:%M"),
                next_dawn[1].strftime("%H:%M"),
            )
        elif dusk_x < chart_end:
            shading.shade(dusk_x, chart_end)
            logger.debug("  Shaded dusk(%s) to chart end", dusk_time.strftime("%H:%M"))


def _next_dawn_after(dawns: Sequence[Tuple[float, datetime]], dusk_x: float) -> Optional[Tuple[float, datetime]]:
    return next((dawn for dawn in dawns if dawn[0] > dusk_x), None)


def add_vertical_line_annotations(
    ax,
    vertical_lines: Optional[Sequence[Tuple[datetime, str, str]]],
    *,
    is_temperature_chart: bool,
    local_timezone: Optional[tzinfo],
) -> None:
    """
    Draw vertical annotations (solar noon, midnight, etc.) on top of the chart.

    Args:
        ax: Matplotlib axis to annotate.
        vertical_lines: Tuples of (datetime, color, label).
        is_temperature_chart: Whether the chart uses localized timestamps.
        local_timezone: Local timezone used for temperature charts.
    """
    if not vertical_lines:
        return

    for line_datetime, line_color, line_label in vertical_lines:
        if is_temperature_chart and local_timezone:
            if line_datetime.tzinfo is None:
                line_datetime_utc = line_datetime.replace(tzinfo=timezone.utc)
            else:
                line_datetime_utc = line_datetime.astimezone(timezone.utc)
            line_datetime_converted = line_datetime_utc.astimezone(local_timezone).replace(tzinfo=None)
        else:
            line_datetime_converted = line_datetime.replace(tzinfo=None) if line_datetime.tzinfo is not None else line_datetime

        line_x = mdates.date2num(line_datetime_converted)

        if "midnight" in line_label.lower():
            color = "blue"
            linewidth = 3
            alpha = 0.9
        else:
            color = line_color
            linewidth = 2
            alpha = 0.8

        ax.axvline(
            x=float(line_x),
            color=color,
            linestyle="-",
            alpha=alpha,
            linewidth=linewidth,
            label=line_label,
        )
