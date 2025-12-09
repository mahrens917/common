"""String helper utilities for the market lifecycle monitor."""

from typing import Any, Dict


def coerce_optional_str(payload: Dict[str, Any], field: str) -> str:
    """Ensure optional string fields return a string representation."""
    value = payload.get(field)
    if value is None:
        return ""
    return str(value)
