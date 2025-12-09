"""Field conversion utilities for orderbook processing."""

from typing import Any, Optional

from src.common.redis_protocol.kalshi_store.utils_coercion import (
    convert_numeric_field as _convert_numeric_field,
)
from src.common.redis_protocol.kalshi_store.utils_coercion import (
    string_or_default as _string_or_default,
)


class FieldConverter:
    """Converts and validates orderbook field values."""

    @staticmethod
    def convert_numeric_field(value: Any) -> Optional[float]:
        """Convert a field value to numeric format for proper data storage."""
        return _convert_numeric_field(value)

    @staticmethod
    def string_or_default(value: Any, default: str = "") -> str:
        """Convert value to string or return default."""
        return _string_or_default(value, default)
