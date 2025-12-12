"""
Canonical numeric conversion utilities.

This module provides standardized functions for converting values to numeric types
with different error handling strategies. All float coercion implementations across
the codebase should delegate to these functions.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def coerce_float_strict(value: Any) -> float:
    """
    Convert value to float with strict error handling.

    Raises ValueError if conversion fails. Use this when the value MUST be a valid
    float and any failure is a critical error.

    Args:
        value: Value to convert (int, float, str, bytes, etc.)

    Returns:
        Float value

    Raises:
        ValueError: If value cannot be converted to float

    Examples:
        >>> coerce_float_strict("3.14")
        3.14
        >>> coerce_float_strict(42)
        42.0
        >>> coerce_float_strict("invalid")  # Raises ValueError
    """
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")

    try:
        return float(value)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ValueError(f"Cannot convert {type(value).__name__} to float: {value!r}") from exc


def coerce_float_optional(value: Any) -> Optional[float]:
    """
    Convert value to float with optional error handling.

    Returns None if conversion fails. Use this when the value may or may not be
    convertible to float and None is an acceptable result.

    Args:
        value: Value to convert (int, float, str, bytes, None, etc.)

    Returns:
        Float value or None if conversion fails

    Examples:
        >>> coerce_float_optional("3.14")
        3.14
        >>> coerce_float_optional(None)
        None
        >>> coerce_float_optional("invalid")
        None
    """
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")

    try:
        return float(value)
    except (ValueError, TypeError):  # policy_guard: allow-silent-handler
        return None


def coerce_float_default(value: Any, value_on_error: float) -> float:
    """
    Convert value to float with explicit default.

    Returns specified fallback value if conversion fails. Use this when you need
    a guaranteed float return value with a known fallback.

    Args:
        value: Value to convert (int, float, str, bytes, etc.)
        value_on_error: Fallback value to return if conversion fails

    Returns:
        Float value or fallback value if conversion fails

    Examples:
        >>> coerce_float_default("3.14", 0.0)
        3.14
        >>> coerce_float_default("invalid", 0.0)
        0.0
        >>> coerce_float_default(None, -1.0)
        -1.0
    """
    result = coerce_float_optional(value)
    return result if result is not None else value_on_error


def coerce_int_strict(value: Any) -> int:
    """
    Convert value to int with strict error handling.

    Raises ValueError if conversion fails. Use this when the value MUST be a valid
    integer and any failure is a critical error.

    Args:
        value: Value to convert (int, float, str, bytes, etc.)

    Returns:
        Integer value

    Raises:
        ValueError: If value cannot be converted to int

    Examples:
        >>> coerce_int_strict("42")
        42
        >>> coerce_int_strict(3.14)  # Truncates
        3
        >>> coerce_int_strict("invalid")  # Raises ValueError
    """
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")

    try:
        return int(value)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        raise ValueError(f"Cannot convert {type(value).__name__} to int: {value!r}") from exc


def coerce_int_optional(value: Any) -> Optional[int]:
    """
    Convert value to int with optional error handling.

    Returns None if conversion fails. Use this when the value may or may not be
    convertible to int and None is an acceptable result.

    Args:
        value: Value to convert (int, float, str, bytes, None, etc.)

    Returns:
        Integer value or None if conversion fails

    Examples:
        >>> coerce_int_optional("42")
        42
        >>> coerce_int_optional(None)
        None
        >>> coerce_int_optional("invalid")
        None
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")

    try:
        return int(value)
    except (ValueError, TypeError):  # policy_guard: allow-silent-handler
        return None


def coerce_int_default(value: Any, value_on_error: int) -> int:
    """
    Convert value to int with explicit default.

    Returns specified fallback value if conversion fails. Use this when you need
    a guaranteed int return value with a known fallback.

    Args:
        value: Value to convert (int, float, str, bytes, etc.)
        value_on_error: Fallback value to return if conversion fails

    Returns:
        Integer value or fallback value if conversion fails

    Examples:
        >>> coerce_int_default("42", 0)
        42
        >>> coerce_int_default("invalid", 0)
        0
        >>> coerce_int_default(None, -1)
        -1
    """
    result = coerce_int_optional(value)
    return result if result is not None else value_on_error
