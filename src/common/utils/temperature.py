"""Temperature conversion utilities shared across the pipeline."""

from __future__ import annotations

import math
from typing import Optional


def celsius_to_fahrenheit(value_c: Optional[float]) -> float:
    """Convert Celsius to Fahrenheit, preserving NaNs.

    Args:
        value_c: Temperature in Celsius, or None.

    Returns:
        Temperature in Fahrenheit. Returns NaN if input is None or NaN.
    """
    if value_c is None:
        return float("nan")
    value = float(value_c)
    if math.isnan(value):  # type: ignore[arg-type]
        return float("nan")
    return (value * 9.0 / 5.0) + 32.0
