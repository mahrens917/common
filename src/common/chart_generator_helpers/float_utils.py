"""Shared float parsing helpers for chart generator components."""

from typing import Optional

from common.parsing_utils import safe_float_parse


def safe_float(value: Optional[str]) -> Optional[float]:
    """Parse a float value while rejecting NaN/inf and treating empties as None."""
    if value in (None, ""):
        return None
    try:
        return safe_float_parse(value, allow_nan_inf=False)
    except ValueError:
        return None
