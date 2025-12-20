from __future__ import annotations

"""Parameter dataclasses for astronomical event processor"""


from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Callable, List, Tuple


@dataclass
class AstronomicalEventProcessorParams:
    """Parameters for processing daily astronomical events"""

    current_date: datetime
    latitude: float
    longitude: float
    start_date: datetime
    end_date: datetime
    local_tz: tzinfo | None
    vertical_lines: List[Tuple[datetime, str, str]]
    dawn_dusk_periods: List[Tuple[datetime, datetime]]
    calculate_solar_noon_utc: Callable
    calculate_local_midnight_utc: Callable
    calculate_dawn_utc: Callable
    calculate_dusk_utc: Callable
