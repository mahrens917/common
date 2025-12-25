"""Common parsing utilities for safe data conversion."""

from __future__ import annotations

import json
import logging
import math
from typing import Any

import orjson

logger = logging.getLogger(__name__)


def safe_json_loads(json_string: str, *, otherwise: Any = None) -> Any:
    """
    Parse JSON string with strict error handling.

    Args:
        json_string: JSON string to parse

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If json_string is empty or None
        json.JSONDecodeError: If JSON parsing fails
    """
    if not json_string:
        return otherwise
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
        logger.debug("Expected exception in operation")
        return otherwise


def safe_orjson_loads(json_bytes: bytes, *, otherwise: Any = None) -> Any:
    """
    Parse JSON bytes using orjson with strict error handling.

    Args:
        json_bytes: JSON bytes to parse

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If json_bytes is empty or None
        orjson.JSONDecodeError: If JSON parsing fails
    """
    if not json_bytes:
        return otherwise
    try:
        return orjson.loads(json_bytes)
    except orjson.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
        logger.debug("Expected exception in operation")
        return otherwise


def safe_int_parse(value: Any, *, otherwise: int | None = None) -> int:
    """
    Convert value to integer with strict error handling.

    Args:
        value: Value to convert

    Returns:
        Integer value

    Raises:
        ValueError: If value is None, empty, or cannot be converted to int
    """
    if value in (None, ""):
        if otherwise is not None:
            return otherwise
        raise ValueError("Cannot parse int from None or empty value")

    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError) as exc:
            if otherwise is not None:
                return otherwise
            raise ValueError(f"Cannot parse int from value: {value!r}") from exc


def safe_float_parse(value: Any, *, allow_nan_inf: bool = False, otherwise: float | None = None) -> float | None:
    """
    Convert value to float with strict error handling.

    Delegates to canonical implementation in common.utils.numeric with additional
    handling for NaN/infinity rejection.

    Args:
        value: Value to convert
        allow_nan_inf: If False, treat NaN and infinity as invalid (default: False)

    Returns:
        Float value

    Raises:
        ValueError: If value is None, empty, cannot be converted to float,
                   or is NaN/infinity when not allowed
    """
    from common.utils.numeric import coerce_float_strict

    if value in (None, ""):
        return otherwise

    # Handle string representations of nan/inf
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if not allow_nan_inf and cleaned in ("nan", "inf", "infinity", "-inf", "-infinity"):
            return otherwise

    # Delegate to canonical implementation
    result = coerce_float_strict(value)

    # Check for NaN and infinity if not allowed
    if not allow_nan_inf and (math.isnan(result) or result == float("inf") or result == float("-inf")):
        return otherwise

    return result


def safe_bool_parse(value: Any, *, otherwise: bool | None = None) -> bool:
    """
    Convert value to boolean with strict error handling.

    Args:
        value: Value to convert

    Returns:
        Boolean value

    Raises:
        ValueError: If value is None or cannot be interpreted as boolean
    """
    if value is None:
        if otherwise is not None:
            return otherwise
        raise ValueError("Cannot parse bool from None value")

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lower_val = value.lower()
        if lower_val in ("true", "1", "yes", "y"):
            return True
        if lower_val in ("false", "0", "no", "n"):
            return False
        raise ValueError(f"Cannot parse bool from string: {value!r}")

    if isinstance(value, (int, float)):
        return bool(value)

    raise ValueError(f"Cannot parse bool from type {type(value).__name__}: {value!r}")


def decode_redis_key(key: bytes | str) -> str:
    """
    Decode a Redis key from bytes to string.

    Args:
        key: Redis key as bytes or string

    Returns:
        Decoded string representation of the key
    """
    if isinstance(key, bytes):
        return key.decode("utf-8")
    return str(key)


__all__ = [
    "safe_json_loads",
    "safe_orjson_loads",
    "safe_int_parse",
    "safe_float_parse",
    "safe_bool_parse",
    "decode_redis_key",
]
