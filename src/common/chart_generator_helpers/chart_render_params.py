from __future__ import annotations

"""Parameter objects for chart rendering to reduce function argument counts"""


from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

if TYPE_CHECKING:
    from datetime import datetime

    from matplotlib.axes import Axes

    from common.chart_components import PredictionOverlayResult
    from common.chart_generator.contexts import ChartStatistics, ChartTimeContext


@dataclass
class ChartTypeFlags:
    """Flags indicating chart type"""

    is_pnl_chart: bool
    is_price_chart: bool
    is_temperature_chart: bool


@dataclass
class PredictionData:
    """Prediction-related data"""

    timestamps: Optional[List[datetime]]
    values: Optional[List[float]]
    uncertainties: Optional[List[float]]


@dataclass
class ChartStyling:
    """Chart styling configuration"""

    chart_title: str
    y_label: str
    value_formatter: Optional[Callable]
    line_color: Optional[str] = None


@dataclass
class ChartContextData:
    """Core chart context and statistics"""

    ax: Axes
    values: List[float]
    stats: ChartStatistics
    time_context: ChartTimeContext
    overlay_result: PredictionOverlayResult


@dataclass
class TemperatureChartData:
    """Temperature-specific chart data"""

    kalshi_strikes: Optional[List[float]]
    station_icao: Optional[str]
    station_coordinates: Optional[Tuple[float, float]]
    dawn_dusk_periods: list
    vertical_lines: list
