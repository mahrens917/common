"""
Property accessor for DailyMaxState to reduce class line count.

This module provides a PropertyAccessor class that encapsulates all property
getter/setter pairs for the DailyMaxState class, maintaining backward compatibility
while keeping the main class under the 120-line limit.
"""

from typing import Any, Dict


class PropertyAccessor:
    """
    Provides property access to DailyMaxState internal state.

    This class encapsulates all property getter/setter pairs to reduce
    the line count of the main DailyMaxState class while maintaining
    backward compatibility with existing code.

    Supported properties:
    - max_temp_c: Maximum temperature in Celsius
    - precision: Temperature precision in Celsius
    - source: Data source name
    - timestamp: Timestamp of maximum temperature observation
    - hourly_max_temp_c: Hourly-only maximum temperature in Celsius
    - hourly_timestamp: Timestamp of hourly maximum temperature observation
    """

    # Define allowed state keys for validation
    _ALLOWED_KEYS = frozenset(
        [
            "max_temp_c",
            "precision",
            "source",
            "timestamp",
            "hourly_max_temp_c",
            "hourly_timestamp",
        ]
    )

    def __init__(self, state: Dict[str, Any]) -> None:
        """
        Initialize property accessor with state dictionary.

        Args:
            state: Internal state dictionary to access
        """
        object.__setattr__(self, "_state", state)

    def __getattr__(self, name: str) -> Any:
        """Get attribute from internal state."""
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if name in self._ALLOWED_KEYS:
            return self._state[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute in internal state."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        elif name in self._ALLOWED_KEYS:
            self._state[name] = value
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
