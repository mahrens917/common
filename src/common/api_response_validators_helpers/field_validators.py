"""Generic field validation helpers."""

from datetime import datetime
from typing import Any, List, Mapping

from common.validation.required_fields import validate_required_fields as _validate_required_fields_common


def validate_required_fields(data: Mapping[str, Any], required_fields: List[str], prefix: str = "") -> None:
    """Validate that all required fields are present in data."""

    def _error_factory(missing: list[str], payload: Mapping[str, Any]) -> ValueError:
        return ValueError(f"{prefix}Missing required fields: {missing}. Available fields: {list(payload.keys())}")

    _validate_required_fields_common(data, required_fields, on_missing=_error_factory)


def validate_string_field(data: Mapping[str, Any], field: str, prefix: str = "", allow_empty: bool = False) -> None:
    """Validate a string field is present and valid."""
    if not isinstance(data[field], str):
        raise TypeError(f"{prefix}{field} must be string, got: {type(data[field])}")
    if not allow_empty and not data[field]:
        raise ValueError(f"{prefix}{field} cannot be empty")


def validate_timestamp_field(data: Mapping[str, Any], field: str, prefix: str = "") -> None:
    """Validate a timestamp field is parseable."""
    if not isinstance(data[field], str):
        raise TypeError(f"{prefix}{field} must be string timestamp, got: {type(data[field])}")
    try:
        datetime.fromisoformat(data[field].replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"{prefix}Invalid timestamp format in {field}: {data[field]}") from e


def validate_numeric_field(data: Mapping[str, Any], field: str, prefix: str = "", min_value: float = 0.0) -> None:
    """Validate a numeric field is valid and within bounds."""
    if not isinstance(data[field], (int, float)):
        raise TypeError(f"{prefix}{field} must be numeric")
    if data[field] < min_value:
        raise ValueError(f"{prefix}{field} cannot be negative: {data[field]}")
