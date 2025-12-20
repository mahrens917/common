"""Parameter dataclasses for chart generation."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ChartData:
    """Primary data series for chart rendering."""

    timestamps: List[datetime]
    values: List[float]


@dataclass(frozen=True)
class ChartMetadata:
    """Chart metadata including titles and labels."""

    chart_title: str
    y_label: str
    value_formatter_func: Optional[object] = None


@dataclass(frozen=True)
class ChartTypeFlags:
    """Flags indicating chart type and rendering requirements."""

    is_price_chart: bool = False
    is_temperature_chart: bool = False
    is_pnl_chart: bool = False


@dataclass(frozen=True)
class PredictionData:
    """Prediction overlay data."""

    prediction_timestamps: Optional[List[datetime]] = None
    prediction_values: Optional[List[float]] = None
    prediction_uncertainties: Optional[List[float]] = None


@dataclass(frozen=True)
class ChartAnnotations:
    """Annotations and overlays for charts."""

    vertical_lines: Optional[List[Tuple[datetime, str, str]]] = None
    dawn_dusk_periods: Optional[List[Tuple[datetime, datetime]]] = None
    kalshi_strikes: Optional[List[float]] = None


@dataclass(frozen=True)
class ChartStyling:
    """Styling parameters for charts."""

    line_color: Optional[str] = None


@dataclass(frozen=True)
class StationData:
    """Weather station specific data."""

    station_icao: Optional[str] = None
    station_coordinates: Optional[Tuple[float, float]] = None


@dataclass(frozen=True)
class UnifiedChartParameters:
    """Complete set of parameters for unified chart generation."""

    data: ChartData
    metadata: ChartMetadata
    type_flags: ChartTypeFlags
    prediction: PredictionData
    annotations: ChartAnnotations
    styling: ChartStyling
    station: StationData
