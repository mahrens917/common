"""Common formatting utilities."""

from typing import Any

_SECONDS_IN_HOUR = 3600.0
_SECONDS_IN_MINUTE = 60.0


def format_duration(seconds: object) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string (e.g., "1.23h", "45.67m", "12.34s")
    """
    if not isinstance(seconds, (int, float)):
        return "0s"

    amount = float(seconds)
    if amount <= 0:
        return "0s"
    if amount >= _SECONDS_IN_HOUR:
        return f"{amount / _SECONDS_IN_HOUR:.2f}h"
    if amount >= _SECONDS_IN_MINUTE:
        return f"{amount / _SECONDS_IN_MINUTE:.2f}m"
    return f"{amount:.2f}s"


def convert_keys_to_strings(data: Any) -> Any:
    """
    Recursively convert all dictionary keys to strings for JSON serialization.

    Args:
        data: Input data structure (dict, list, or primitive value)

    Returns:
        Data structure with all dictionary keys converted to strings
    """
    if isinstance(data, dict):
        return {str(k): convert_keys_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_keys_to_strings(item) for item in data]
    return data


__all__ = ["format_duration", "convert_keys_to_strings"]
