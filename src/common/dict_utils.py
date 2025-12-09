"""
Shared dictionary utility functions.

Provides consistent dictionary value extraction with type coercion
and base value handling. Consolidates duplicate helper functions
previously scattered across multiple modules.
"""

from typing import Any, Dict, Optional


def mapping_bool(mapping: Optional[Dict[str, Any]], key: str, base_value: bool = False) -> bool:
    """
    Extract boolean value from mapping with type coercion.

    Args:
        mapping: Dictionary to extract from (can be None)
        key: Key to look up
        base_value: Value returned when input is missing or falsy
    """
    if not mapping:
        return base_value

    if key not in mapping:
        return base_value

    value = mapping[key]
    if value is None:
        return base_value

    if isinstance(value, bool):
        return value

    return str(value).lower() == "true"


def mapping_str(mapping: Optional[Dict[str, Any]], key: str, base_value: str = "") -> str:
    """
    Extract string value from mapping with type coercion.

    Args:
        mapping: Dictionary to extract from (can be None)
        key: Key to look up
        base_value: String to return when no valid value exists
    """
    if mapping is None:
        return base_value

    value = mapping.get(key, base_value)
    if value is None:
        return base_value

    return str(value)
