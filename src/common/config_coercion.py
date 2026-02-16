"""Configuration-aware coercion utilities.

Provides type coercion functions that produce structured error messages
with field paths, suitable for validating JSON/dict configuration payloads.
"""

from __future__ import annotations

from typing import Optional

from common.exceptions import ConfigurationError, ConfigurationTypeError

__all__ = [
    "OptionalFloatCoercionError",
    "coerce_bool",
    "coerce_float",
    "coerce_int",
    "coerce_optional_float",
    "coerce_positive_float",
    "coerce_positive_int",
]


def coerce_float(value: object, *, field_path: str) -> float:
    """
    Convert a value to float, raising ConfigurationError if invalid.

    Args:
        value: The value to coerce (int, float, or string representation)
        field_path: Dotted path to the configuration field (for error messages)

    Returns:
        Float value

    Raises:
        ConfigurationError: If the value is empty or cannot be parsed
        ConfigurationTypeError: If the value type is invalid
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ConfigurationError.invalid_field_path(field_path, "must be numeric")
        try:
            return float(stripped)
        except ValueError as exc:
            raise ConfigurationError.invalid_field_path(field_path, "must be numeric") from exc
    raise ConfigurationTypeError.for_field(field_path, "number")


def coerce_int(value: object, *, field_path: str) -> int:
    """
    Convert a value to int, raising ConfigurationError if invalid.

    Args:
        value: The value to coerce (int or string representation)
        field_path: Dotted path to the configuration field (for error messages)

    Returns:
        Integer value

    Raises:
        ConfigurationError: If the value is empty or cannot be parsed
        ConfigurationTypeError: If the value type is invalid (including bool)
    """
    if isinstance(value, bool):
        raise ConfigurationTypeError.for_field(field_path, "integer")
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ConfigurationError.invalid_field_path(field_path, "must be an integer")
        try:
            return int(stripped)
        except ValueError as exc:
            raise ConfigurationError.invalid_field_path(field_path, "must be an integer") from exc
    raise ConfigurationTypeError.for_field(field_path, "integer")


def coerce_bool(value: object, *, field_path: str) -> bool:
    """
    Convert a value to bool, supporting common string representations.

    Args:
        value: The value to coerce (bool or string like "true", "yes", "1", etc.)
        field_path: Dotted path to the configuration field (for error messages)

    Returns:
        Boolean value

    Raises:
        ConfigurationError: If the value cannot be interpreted as boolean
    """
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        truthy = {"true", "yes", "y", "1"}
        falsy = {"false", "no", "n", "0"}
        if lowered in truthy:
            return True
        if lowered in falsy:
            return False
    raise ConfigurationError.invalid_field_path(field_path, "must be a boolean value")


def coerce_positive_float(value: object, *, field_path: str, allow_zero: bool = False) -> float:
    """
    Convert a value to a positive float.

    Args:
        value: The value to coerce
        field_path: Dotted path to the configuration field (for error messages)
        allow_zero: If True, allow zero (non-negative); if False, require > 0

    Returns:
        Positive float value

    Raises:
        ConfigurationError: If the value is not positive (or non-negative if allow_zero)
        ConfigurationTypeError: If the value type is invalid
    """
    numeric = coerce_float(value, field_path=field_path)
    if allow_zero:
        if numeric < 0.0:
            raise ConfigurationError.invalid_field_path(field_path, "must be non-negative")
    elif numeric <= 0.0:
        raise ConfigurationError.invalid_field_path(field_path, "must be a positive number")
    return numeric


def coerce_positive_int(value: object, *, field_path: str) -> int:
    """
    Convert a value to a positive integer.

    Args:
        value: The value to coerce
        field_path: Dotted path to the configuration field (for error messages)

    Returns:
        Positive integer value

    Raises:
        ConfigurationError: If the value is not positive
        ConfigurationTypeError: If the value type is invalid
    """
    numeric = coerce_int(value, field_path=field_path)
    if numeric < 1:
        raise ConfigurationError.invalid_field_path(field_path, "must be >= 1")
    return numeric


class OptionalFloatCoercionError(ValueError):
    """Raised when optional float coercion fails for invalid input."""

    @classmethod
    def invalid_numeric_item(cls, value: object) -> "OptionalFloatCoercionError":
        return cls(f"Cannot coerce numpy-like value to float: {value!r}")

    @classmethod
    def invalid_string(cls, text: str) -> "OptionalFloatCoercionError":
        return cls(f"Cannot coerce string to float: {text!r}")

    @classmethod
    def unsupported_type(cls, value: object) -> "OptionalFloatCoercionError":
        return cls(f"Unsupported type for float coercion: {type(value).__name__}")


def _parse_numeric_item(value: object) -> float:
    """Parse value with .item() method (numpy types).

    Raises:
        OptionalFloatCoercionError: If coercion fails
    """
    try:
        return float(value.item())  # type: ignore[union-attr]
    except (ValueError, AttributeError) as exc:
        raise OptionalFloatCoercionError.invalid_numeric_item(value) from exc


def _parse_string_to_float(value: str) -> Optional[float]:
    """Parse non-empty string to float, returning None for empty strings.

    Raises:
        OptionalFloatCoercionError: If non-empty string cannot be parsed
    """
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise OptionalFloatCoercionError.invalid_string(text) from exc


def coerce_optional_float(value: object) -> Optional[float]:
    """
    Convert a value to float, returning None only for empty strings.

    This is a strict coercion for optional numeric values that raises
    on invalid input rather than silently returning None.

    Args:
        value: The value to coerce (int, float, np.generic, or string)

    Returns:
        Float value or None if the input is an empty string

    Raises:
        OptionalFloatCoercionError: If value cannot be converted to float
    """
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "item"):
        return _parse_numeric_item(value)
    if isinstance(value, str):
        return _parse_string_to_float(value)
    raise OptionalFloatCoercionError.unsupported_type(value)
