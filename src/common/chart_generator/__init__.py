from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from common.config.redis_schema import get_schema_config
from common.history_tracker import PriceHistoryTracker, WeatherHistoryTracker
from common.redis_schema import parse_kalshi_market_key
from src.common.price_path_calculator import (
    MostProbablePricePathCalculator,
    PricePathComputationError,
)

if TYPE_CHECKING:
    from src.monitor.trade_visualizer import TradeVisualizer

from . import dependencies as _deps
from .contexts import AstronomicalFeatures, ChartStatistics, ChartTimeContext, WeatherChartSeries
from .exceptions import InsufficientDataError, ProgressNotificationError
from .runtime import ChartGenerator

LOGGER_NAME = "src.monitor.chart_generator"
logger = logging.getLogger(LOGGER_NAME)

# Re-export matplotlib/numpy modules used heavily in tests for monkeypatching.
plt = _deps.plt
mdates = _deps.mdates
mcolors = _deps.mcolors
ticker = _deps.ticker
np = _deps.np
asyncio = _deps.asyncio
os = _deps.os
tempfile = _deps.tempfile
time = _deps.time

__all__ = [
    "ChartGenerator",
    "InsufficientDataError",
    "ProgressNotificationError",
    "MostProbablePricePathCalculator",
    "PricePathComputationError",
    "parse_kalshi_market_key",
    "PriceHistoryTracker",
    "WeatherHistoryTracker",
    "TradeVisualizer",
    "get_schema_config",
    "datetime",
    "ChartTimeContext",
    "ChartStatistics",
    "WeatherChartSeries",
    "AstronomicalFeatures",
    "logger",
    "plt",
    "mdates",
    "mcolors",
    "ticker",
    "np",
    "asyncio",
    "os",
    "tempfile",
    "time",
]


def __getattr__(name: str):
    """Lazy loading for monitor-dependent imports."""
    if name == "TradeVisualizer":
        from src.monitor.trade_visualizer import TradeVisualizer

        return TradeVisualizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
