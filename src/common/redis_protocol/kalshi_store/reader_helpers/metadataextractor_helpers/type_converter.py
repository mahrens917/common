"""
Type Converter - Handle type conversions and normalization

Converts values to strings and normalizes Redis hash responses.
"""

from typing import Any, Dict

from src.common.redis_protocol.kalshi_store.utils_coercion import (
    string_or_default as _string_or_default,
)


class TypeConverter:
    """Handle type conversions for metadata extraction"""

    @staticmethod
    def string_or_default(value: Any, default: str = "") -> str:
        """
        Convert value to string or return default

        Args:
            value: Value to convert
            default: Default value if conversion fails

        Returns:
            String representation or default
        """
        return _string_or_default(value, default)

    @staticmethod
    def normalize_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Convert Redis hash responses to a str-keyed dictionary.

        Args:
            raw_hash: Raw Redis hash with potentially byte keys/values

        Returns:
            Normalized dictionary with string keys
        """
        normalised: Dict[str, Any] = {}
        for key, value in raw_hash.items():
            if isinstance(key, bytes):
                key = key.decode("utf-8", "ignore")
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")
            normalised[str(key)] = value
        return normalised
