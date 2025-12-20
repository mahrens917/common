"""Parameter dataclasses for trade visualization."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class TradeAnnotationParameters:
    """Parameters for annotating trades on charts."""

    ax: object
    station_icao: Optional[str]
    naive_timestamps: Optional[Sequence[datetime]]
    plot_timestamps: Sequence[datetime]
    is_temperature_chart: bool
    kalshi_strikes: Optional[Sequence[float]]
    trade_visualizer_cls: Optional[type] = None


@dataclass(frozen=True)
class TradeShadingParameters:
    """Parameters for fetching and applying trade shadings."""

    trade_visualizer: object
    ax: object
    station_icao: str
    naive_timestamps: Sequence[datetime]
    plot_timestamps: Sequence[datetime]
    kalshi_strikes: Sequence[float]
