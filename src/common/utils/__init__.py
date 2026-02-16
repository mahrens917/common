"""
Common utilities package.

This package contains shared utility functions used across the application.

ARCHITECTURAL NOTE: The system uses a hybrid approach:
- Micro-price (volume-weighted) for: GP surface fitting, spot price calculations, surface reconstruction
- Mid-price (simple average) for: Breeden-Litzenberger second derivative calculations and adaptive step sizing
- Both approaches serve specific mathematical purposes in the options pricing pipeline
"""

# Utility imports are managed by specific modules that need them.
# The system uses both micro-price and mid-price calculations where mathematically appropriate.

from typing import List

from .solar import (
    SolarTimes,
    compute_day_of_year_encoding,
    compute_solar_diurnal,
    compute_solar_diurnal_from_iso,
    compute_solar_times,
)

__all__: List[str] = [
    "SolarTimes",
    "compute_day_of_year_encoding",
    "compute_solar_diurnal",
    "compute_solar_diurnal_from_iso",
    "compute_solar_times",
]
