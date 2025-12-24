"""Configuration objects for chart generator parameters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from common.chart_components.prediction_overlay import PredictionOverlayResult
from common.chart_generator.contexts import ChartStatistics, ChartTimeContext


@dataclass(frozen=True)
class ChartComponentData:
    """Data for applying chart components."""

    ax: Any  # Axes
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
    add_kalshi_strike_lines_func: Any
    add_comprehensive_temperature_labels_func: Any
    mdates: Any


@dataclass(frozen=True)
class AxesLimitsConfig:
    """Configuration for axes limits."""

    ax: Any
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


@dataclass(frozen=True)
class ChartDataPrepInput:
    """Input data for preparing chart data."""

    time_utc: Any
    time_local: Any
    underlying_data: Any
    raw_values: List[float]
    dataset_start_utc: Any
    dataset_end_utc: Any
    dataset_start_local: Any
    dataset_end_local: Any
    chart_start_local: Any
    chart_end_local: Any
    local_timezone: Any
    value_formatter: Optional[Callable]
    overlay_result: PredictionOverlayResult


@dataclass(frozen=True)
class ChartTitlesLabelsData:
    """Data for applying titles and labels."""

    ax: Any
    chart_title: str
    y_label: str
    stats: ChartStatistics
    time_context: ChartTimeContext
    is_temperature_chart: bool
    is_pnl_chart: bool
    station_icao: Optional[str]


@dataclass(frozen=True)
class PrimarySeriesRenderData:
    """Data for rendering primary series."""

    ax: Any
    time: List
    values: List[float]
    is_temperature_chart: bool
    is_pnl_chart: bool
    is_price_chart: bool
    chart_title: str
    local_timezone: Any
    value_formatter: Optional[Callable]


@dataclass(frozen=True)
class AstronomicalEventData:
    """Data for processing astronomical events."""

    current_date: Any  # datetime
    latitude: float
    longitude: float
    start_date: Any  # datetime
    end_date: Any  # datetime
    local_tz: Any  # tzinfo | None
    vertical_lines: List
    dawn_dusk_periods: List
    calculate_solar_noon_utc: Callable
    calculate_local_midnight_utc: Callable
    calculate_dawn_utc: Callable
    calculate_dusk_utc: Callable


@dataclass(frozen=True)
class ChartPreparationData:
    """Data for preparing and rendering series."""

    ax: Any
    timestamps: List
    values: List[float]
    prediction_timestamps: Optional[List]
    prediction_values: Optional[List[float]]
    prediction_uncertainties: Optional[List[float]]
    station_coordinates: Optional[Any]  # Tuple[float, float]
    is_temperature_chart: bool
    is_price_chart: bool
    is_pnl_chart: bool
    line_color: Optional[str]
    value_formatter: Any
    mdates: Any
    np: Any


@dataclass(frozen=True)
class PrimarySeriesRenderConfig:
    """Configuration for rendering primary series."""

    ax: Any
    values: List[float]
    plot_color: str
    stats: ChartStatistics
    time_context: ChartTimeContext
    is_temperature_chart: bool
    is_pnl_chart: bool
    is_price_chart: bool
    mdates: Any


@dataclass(frozen=True)
class StrikeCollectionData:
    """Data for collecting strikes from Redis."""

    current_index: int
    valid_striketimes: List[int]
    strike_data_points: List
    redis_client: Any
    currency: str
    unix_timestamp: int
    expiry_striketimes: List[int]


@dataclass(frozen=True)
class StatisticsFormattingConfig:
    """Configuration for applying statistics and formatting."""

    ax: Any  # Axes
    stats: Any  # ChartStatistics
    values: List[float]
    value_formatter: Optional[Callable]
    is_price_chart: bool
    is_temperature_chart: bool
    is_pnl_chart: bool
    format_y_axis_func: Any


@dataclass(frozen=True)
class StrikeCollectionContext:
    """Context for collecting strikes from Redis key."""

    redis_client: Any
    key_str: str
    parse_fn: Any  # Callable
    today_et: Any  # date
    et_timezone: Any
    today_market_date: str
    strikes: Any  # set[float]
