from __future__ import annotations

"""Shared parameter dataclasses for chart generator helpers to reduce function parameter counts."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from common.chart_components import PredictionOverlayResult
    from common.chart_generator.contexts import ChartStatistics, ChartTimeContext


@dataclass
class AxesLimitsParams:
    """Parameters for configuring axes limits and baselines."""

    ax: Axes
    values: List[float]
    stats: ChartStatistics
    time_context: ChartTimeContext
    overlay_result: PredictionOverlayResult
    prediction_values: Optional[List[float]]
    prediction_uncertainties: Optional[List[float]]
    is_pnl_chart: bool
    is_price_chart: bool
    is_temperature_chart: bool
    kalshi_strikes: Optional[List[float]]
    mdates: Any


@dataclass
class BaselineParams:
    """Parameters for adding baseline lines."""

    ax: Axes
    stats: ChartStatistics
    is_pnl_chart: bool
    is_price_chart: bool
    is_temperature_chart: bool
    kalshi_strikes: Optional[List[float]]


@dataclass
class ChartComponentParams:
    """Parameters for applying chart components."""

    ax: Axes
    values: List[float]
    stats: ChartStatistics
    time_context: ChartTimeContext
    overlay_result: PredictionOverlayResult
    prediction_values: Optional[List[float]]
    prediction_uncertainties: Optional[List[float]]
    vertical_lines: Any
    dawn_dusk_periods: Any
    is_pnl_chart: bool
    is_price_chart: bool
    is_temperature_chart: bool
    kalshi_strikes: Optional[List[float]]
    chart_title: str
    y_label: str
    station_icao: Optional[str]
    value_formatter: Optional[Callable]
    add_kalshi_strike_lines_func: Callable
    add_comprehensive_temperature_labels_func: Callable
    mdates: Any


@dataclass
class StatisticsFormattingParams:
    """Parameters for applying statistics and formatting."""

    ax: Axes
    stats: ChartStatistics
    values: List[float]
    value_formatter: Optional[Callable]
    is_price_chart: bool
    is_temperature_chart: bool
    is_pnl_chart: bool
    format_y_axis_func: Callable


@dataclass
class SeriesRenderParams:
    """Parameters for preparing and rendering series."""

    ax: Axes
    timestamps: List[datetime]
    values: List[float]
    prediction_timestamps: Optional[List[datetime]]
    prediction_values: Optional[List[float]]
    prediction_uncertainties: Optional[List[float]]
    station_coordinates: Optional[Tuple[float, float]]
    is_temperature_chart: bool
    is_price_chart: bool
    is_pnl_chart: bool
    line_color: Optional[str]
    value_formatter: Optional[Callable]
    mdates: Any
    np: Any


@dataclass
class ChartTitlesParams:
    """Parameters for applying titles and labels."""

    ax: Axes
    chart_title: str
    y_label: str
    stats: ChartStatistics
    time_context: ChartTimeContext
    is_temperature_chart: bool
    is_pnl_chart: bool
    station_icao: Optional[str]


@dataclass
class StrikeGathererParams:
    """Parameters for gathering strikes."""

    redis_client: Any
    tokens: Any
    parse_fn: Callable
    today_et: Any
    et_timezone: Any
    today_market_date: str


@dataclass
class CanonicalTokenResolutionParams:
    """Parameters for canonical token resolution."""

    redis_client: Any
    canonical_token: str
    today_market_date: str
    parse_fn: Callable
    today_et: Any
    et_timezone: Any


@dataclass
class CanonicalTokenFallbackParams:
    """Parameters for canonical token fallback handling."""

    redis_client: Any
    canonical_token: str
    today_market_date: str
    parse_fn: Callable
    today_et: Any
    et_timezone: Any


@dataclass
class BreakdownChartParams:
    """Parameters for generating breakdown charts."""

    data: Dict[str, int]
    title: str
    xlabel: str
    filename_suffix: str
    np: Any
    plt: Any
    tempfile: Any


@dataclass
class PrimarySeriesParams:
    """Parameters for rendering primary series."""

    ax: Axes
    values: List[float]
    plot_color: str
    stats: ChartStatistics
    time_context: ChartTimeContext
    is_temperature_chart: bool
    is_pnl_chart: bool
    is_price_chart: bool
    mdates: Any


@dataclass
class StatisticsTextParams:
    """Parameters for adding statistics text."""

    ax: Axes
    stats: ChartStatistics
    values: List[float]
    value_formatter: Optional[Callable[[float], str]]
    is_price_chart: bool
    is_temperature_chart: bool
    is_pnl_chart: bool


@dataclass
class TimeAxisParams:
    """Parameters for configuring time axis."""

    ax: Any
    timestamps: List[datetime]
    chart_type: str
    station_coordinates: Optional[Tuple[float, float]]
    mdates: Any
    plt: Any


@dataclass
class TradeAnnotationParams:
    """Parameters for trade annotation."""

    ax: Axes
    station_icao: Optional[str]
    time_context: Any
    is_temperature_chart: bool
    kalshi_strikes: Optional[List[float]]
    resolve_trade_visualizer_func: Callable
