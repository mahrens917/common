from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ChartTimeContext:
    """Precomputed timestamps used throughout chart rendering."""

    naive: List[datetime]
    prediction: Optional[List[datetime]]
    axis: List[datetime]
    localized: Optional[List[datetime]]
    local_timezone: Optional[tzinfo]
    plot: List[datetime]


@dataclass(frozen=True)
class ChartStatistics:
    """Simple container for series statistics."""

    min_value: float
    max_value: float
    mean_value: float


@dataclass(frozen=True)
class WeatherChartSeries:
    """Sorted temperature series for a weather station."""

    timestamps: List[datetime]
    temperatures: List[float]
    current_temperature: float


@dataclass(frozen=True)
class AstronomicalFeatures:
    """Precomputed astronomical overlays for temperature charts."""

    vertical_lines: List[Tuple[datetime, str, str]]
    dawn_dusk_periods: Optional[List[Tuple[datetime, datetime]]]
