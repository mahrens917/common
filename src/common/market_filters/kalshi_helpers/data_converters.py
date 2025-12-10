"""Data conversion utilities for Kalshi market validation."""

import math
from datetime import datetime
from typing import Any, Optional

from ...time_helpers.expiry_conversions import parse_expiry_datetime as _parse_expiry_datetime


def decode_payload(value: Any) -> Any:
    """Decode bytes to string if needed."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return value


def to_float_value(value: Any) -> Optional[float]:
    """Convert value to float, returning None on failure. Delegates to canonical implementation."""
    from common.utils.numeric import coerce_float_optional

    decoded = decode_payload(value)
    if decoded in ("None",):
        return None
    result = coerce_float_optional(decoded)
    if result is None:
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def to_int_value(value: Any) -> Optional[int]:
    """Convert value to int, returning None on failure. Delegates to canonical implementation."""
    from common.utils.numeric import coerce_int_optional

    decoded = decode_payload(value)
    if decoded in ("None",):
        return None
    result = coerce_int_optional(decoded)
    if result is not None:
        return result
    try:
        return int(float(decoded))
    except (ValueError, TypeError):
        return None


def parse_expiry_datetime(expiry_str: str) -> datetime:
    """Delegate to canonical expiry parser to maintain consistent timezone handling."""
    return _parse_expiry_datetime(expiry_str)
