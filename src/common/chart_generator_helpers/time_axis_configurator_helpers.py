from __future__ import annotations

"""Helper functions for time axis configuration."""


import logging
from datetime import datetime
from typing import List

logger = logging.getLogger("src.monitor.chart_generator")

DEFAULT_TICK_INTERVAL_MINUTES_BASE = 10
DEFAULT_TICK_INTERVAL_MINUTES_NEAR = 30
DEFAULT_TICK_INTERVAL_MINUTES_FAR = 120


def configure_temperature_axis(ax, timestamps: List[datetime], *, mdates, plt) -> None:
    """Configure x-axis for temperature charts with hourly ticks."""
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # No minor ticks for cleaner appearance
    from matplotlib.ticker import NullLocator

    ax.xaxis.set_minor_locator(NullLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_xlabel("")


def configure_default_axis(ax, timestamps: List[datetime], time_range_hours: float, *, mdates, plt) -> None:
    """Configure x-axis for non-temperature charts with dynamic tick spacing."""
    from common.config_loader import load_config

    config = load_config("monitor_constants.json")
    min_bucket_hours_near = config["chart_generation"]["min_bucket_hours_near"]
    min_bucket_hours_mid = config["chart_generation"]["min_bucket_hours_mid"]
    minutes_per_hour = config["time_limits"]["seconds_per_minute"]

    if time_range_hours <= 1:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_BASE
    elif time_range_hours <= min_bucket_hours_near:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_NEAR
    elif time_range_hours <= min_bucket_hours_mid:
        tick_interval_minutes = minutes_per_hour
    else:
        tick_interval_minutes = DEFAULT_TICK_INTERVAL_MINUTES_FAR

    # Set major ticks
    if tick_interval_minutes >= minutes_per_hour:
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=tick_interval_minutes // minutes_per_hour))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    else:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=tick_interval_minutes))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # Set minor ticks
    minor_interval = max(tick_interval_minutes // 4, 5)
    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=minor_interval))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.set_xlabel("")


def configure_price_axis_locators(total_hours: float, start: datetime, end: datetime, *, mdates):
    """Determine appropriate locators and formatters for price chart axis."""
    from common.config_loader import load_config

    config = load_config("monitor_constants.json")
    far_hours_1 = config["chart_generation"]["bucket_hours_far_2"]
    far_hours_2 = config["chart_generation"]["bucket_hours_far_3"]
    far_hours_3 = config["chart_generation"]["bucket_hours_far_4"]

    if total_hours <= far_hours_1:
        interval_hours = 2
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    elif total_hours <= far_hours_2:
        interval_hours = 4
        major_locator = mdates.HourLocator(interval=interval_hours)
        major_formatter = mdates.DateFormatter("%b %d %H:%M")
        minor_locator = mdates.HourLocator(interval=max(1, interval_hours // 2))
    elif total_hours <= far_hours_3:
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

    return major_locator, major_formatter, minor_locator
