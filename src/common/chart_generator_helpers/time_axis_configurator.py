from __future__ import annotations

"""Helper for configuring time axes on charts"""


import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

logger = logging.getLogger("src.monitor.chart_generator")

# Time range thresholds in hours
_HOURS_SHORT_RANGE = 3
_HOURS_MEDIUM_RANGE = 12
_HOURS_EXTENDED_RANGE = 60
_HOURS_ONE_DAY = 24
_HOURS_FOUR_DAYS = 96
_HOURS_TEN_DAYS = 240

DEFAULT_TICK_INTERVAL_MINUTES_SHORT = 10
DEFAULT_TICK_INTERVAL_MINUTES_MEDIUM = 30
DEFAULT_TICK_INTERVAL_MINUTES_LONG = 60
DEFAULT_TICK_INTERVAL_MINUTES_EXTRA_LONG = 120


class TimeAxisConfigurator:
    """Configures time axes for different chart types"""

    # Declare dynamically-attached methods for static type checking
    def configure_time_axis_with_5_minute_alignment(
        self,
        ax,
        timestamps: List[datetime],
        chart_type: str = "default",
        station_coordinates: Optional[Tuple[float, float]] = None,
        *,
        mdates,
        plt,
    ) -> None:
        """Configure time axis with 5 minute alignment."""
        ...

    def configure_price_chart_axis(self, ax, timestamps: List[datetime], *, mdates, plt) -> None:
        """Configure price chart axis."""
        ...


def _configure_time_axis_with_5_minute_alignment(
    self,
    ax,
    timestamps: List[datetime],
    chart_type: str = "default",
    station_coordinates: Optional[Tuple[float, float]] = None,
    *,
    mdates,
    plt,
):
    if not timestamps:
        logger.warning("No timestamps provided for %s chart", chart_type)
        return
    time_range_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
    if chart_type == "temperature":
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        from matplotlib.ticker import NullLocator

        ax.xaxis.set_minor_locator(NullLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
        ax.set_xlabel("")
        return
    if time_range_hours <= 1:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_SHORT
    elif time_range_hours <= _HOURS_SHORT_RANGE:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_MEDIUM
    elif time_range_hours <= _HOURS_MEDIUM_RANGE:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_LONG
    else:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_EXTRA_LONG
    if tick_interval_minutes >= _HOURS_EXTENDED_RANGE:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=tick_interval_minutes // 60))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    else:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=tick_interval_minutes))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    minor_interval = max(tick_interval_minutes // 4, 5)
    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=minor_interval))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_xlabel("")


def _configure_price_chart_axis(self, ax, timestamps: List[datetime], *, mdates, plt) -> None:
    if not timestamps:
        logger.warning("No timestamps provided for price chart axis configuration")
        return
    start = timestamps[0]
    end = timestamps[-1]
    if end <= start:
        end = start + timedelta(hours=1)
    total_hours = max(1.0, (end - start).total_seconds() / 3600.0)
    if total_hours <= _HOURS_ONE_DAY:
        interval_hours = 2
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    elif total_hours <= _HOURS_FOUR_DAYS:
        interval_hours = 4
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    elif total_hours <= _HOURS_TEN_DAYS:
        interval_hours = 8
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    elif total_hours <= 24 * 14:
        interval_hours = 12
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    else:
        total_days = max(1, int(round((end - start).total_seconds() / 86400.0)))
        interval_days = max(1, total_days // 12)
        major_locator = mdates.DayLocator(interval=interval_days)
        major_formatter = mdates.DateFormatter("%b %d")
        minor_locator = mdates.DayLocator(interval=max(1, interval_days // 2))
    ax.xaxis.set_major_locator(major_locator)
    ax.xaxis.set_major_formatter(major_formatter)
    ax.xaxis.set_minor_locator(minor_locator)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
    ax.set_xlabel("")
    ax.set_xlim(start, end)


setattr(
    TimeAxisConfigurator,
    "configure_time_axis_with_5_minute_alignment",
    _configure_time_axis_with_5_minute_alignment,
)
setattr(TimeAxisConfigurator, "configure_price_chart_axis", _configure_price_chart_axis)
