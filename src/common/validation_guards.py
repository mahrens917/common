"""
Common validation guard helpers used to keep dataclass __post_init__ logic concise.

Each helper focuses on a single check so higher-level validations can compose these
building blocks without introducing additional branching.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Type


def require(condition: bool, error: Exception) -> None:
    """Raise the provided exception when the condition fails."""
    if not condition:
        raise error


def require_instance(value: Any, expected_type: Type[Any], field_name: str) -> None:
    """Ensure a value is an instance of the expected type."""
    require(
        isinstance(value, expected_type),
        TypeError(f"{field_name} must be a {expected_type.__name__} object"),
    )


def require_optional_instance(value: Any, expected_type: Type[Any], field_name: str) -> None:
    """Ensure optional values are either None or of the expected type."""
    if value is None:
        return
    require_instance(value, expected_type, field_name)


def require_non_empty_string(value: Any, field_name: str) -> None:
    """Ensure a string field is present and non-empty."""
    require(isinstance(value, str), TypeError(f"{field_name} must be a string"))
    require(value.strip() != "", ValueError(f"{field_name} cannot be empty"))


def require_date(value: date, field_name: str) -> None:
    """Ensure the provided value is a date."""
    require_instance(value, date, field_name)


def require_datetime(value: datetime, field_name: str) -> None:
    """Ensure the provided value is a datetime."""
    require_instance(value, datetime, field_name)


def require_non_negative(value: int | float, field_name: str) -> None:
    """Ensure numeric values are non-negative."""
    require(value >= 0, ValueError(f"{field_name} cannot be negative: {value}"))


def require_percentage(value: float, field_name: str) -> None:
    """Ensure a floating point value lies within [0, 1]."""
    require(
        0.0 <= value <= 1.0,
        TypeError(f"{field_name} must be between 0.0 and 1.0: {value}"),
    )


def require_keys(data: dict[str, Any], required_keys: Iterable[str], prefix: str) -> None:
    """Ensure all required keys are present in a dictionary."""
    missing = [key for key in required_keys if key not in data]
    require(
        not missing,
        KeyError(f"{prefix} missing required fields: {missing}"),
    )
