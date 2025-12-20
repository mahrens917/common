"""Configuration dataclasses for price path calculator."""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class PricePathCalculatorConfig:
    """Configuration for most probable price path calculator."""

    strike_count: int
    min_moneyness: float
    max_moneyness: float
    timeline_points: int
    min_horizon_days: float
    surface_loader: Optional[Callable] = None
    progress_callback: Optional[Callable] = None
    dependencies: Optional[Any] = None
