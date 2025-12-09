"""Utilities for safe dictionary value extraction and manipulation."""

from typing import Any, Dict, Optional


def get_str(mapping: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    """
    Safely extract string value from dictionary.

    Args:
        mapping: Dictionary to extract from (can be None)
        key: Key to look up
        default: Default value if key missing or None

    Returns:
        String value or default

    Example:
        >>> get_str({"foo": "bar"}, "foo")
        'bar'
        >>> get_str({"foo": 123}, "foo")
        '123'
        >>> get_str(None, "foo", "default")
        'default'
        >>> get_str({"foo": None}, "foo", "default")
        'default'
    """
    if not mapping or key not in mapping or mapping[key] is None:
        return default
    return str(mapping[key])


def get_bool(mapping: Optional[Dict[str, Any]], key: str, default: bool = False) -> bool:
    """
    Safely extract boolean value from dictionary.

    Args:
        mapping: Dictionary to extract from (can be None)
        key: Key to look up
        default: Default value if key missing or None

    Returns:
        Boolean value or default

    Example:
        >>> get_bool({"active": True}, "active")
        True
        >>> get_bool({"active": "true"}, "active")
        True
        >>> get_bool(None, "active")
        False
        >>> get_bool({"active": None}, "active", True)
        True
    """
    if not mapping or key not in mapping or mapping[key] is None:
        return default
    value = mapping[key]
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


__all__ = ["get_str", "get_bool"]
