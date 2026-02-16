"""
Data coercion and type conversion utilities for status reporter.

Provides type-safe conversion from Redis values to Python types with sensible defaults.
"""

from typing import Any, Dict, List

from common.redis_protocol.kalshi_store.utils_coercion import bool_or_default as _bool_or_default
from common.redis_protocol.kalshi_store.utils_coercion import coerce_mapping as _coerce_mapping
from common.redis_protocol.kalshi_store.utils_coercion import coerce_sequence as _coerce_sequence
from common.redis_protocol.kalshi_store.utils_coercion import float_or_default as _float_or_default
from common.redis_protocol.kalshi_store.utils_coercion import int_or_default as _int_or_default
from common.redis_protocol.kalshi_store.utils_coercion import string_or_default as _string_or_default


class DataCoercion:
    """Type-safe data coercion utilities."""

    @staticmethod
    def coerce_mapping(candidate: Any) -> Dict[str, Any]:
        """Safely coerce value to dictionary."""
        return _coerce_mapping(candidate)

    @staticmethod
    def coerce_sequence(candidate: Any) -> List[Any]:
        """Safely coerce value to list."""
        return _coerce_sequence(candidate)

    @staticmethod
    def bool_or_default(value: Any, value_on_error: bool) -> bool:
        """Extract boolean or return value on error."""
        return _bool_or_default(value, value_on_error)

    @staticmethod
    def int_or_default(value: Any, value_on_error: int = 0) -> int:
        """Extract integer or return value on error."""
        return _int_or_default(value, value_on_error)

    @staticmethod
    def float_or_default(value: Any, value_on_error: float = 0.0) -> float:
        """Extract float or return value on error."""
        return _float_or_default(value, value_on_error)

    @staticmethod
    def string_or_default(value: Any, value_on_error: str) -> str:
        """Extract string or return value on error."""
        return _string_or_default(value, value_on_error)
