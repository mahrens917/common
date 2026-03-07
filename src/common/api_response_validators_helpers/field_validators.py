"""Generic field and series validation helpers."""

from __future__ import annotations

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


def validate_series_item(series_data: Mapping[str, Any], idx: int) -> None:
    """Validate basic series item structure."""
    required_fields = ["ticker", "title", "category"]
    missing_fields = [field for field in required_fields if field not in series_data]

    if missing_fields:
        raise ValueError(f"Series {idx} missing required fields: {missing_fields}. " f"Available fields: {list(series_data.keys())}")


def validate_series_strings(series_data: Mapping[str, Any], idx: int) -> None:
    """Validate string fields in series data."""
    required_fields = ["ticker", "title", "category"]
    for field in required_fields:
        if not isinstance(series_data[field], str):
            raise TypeError(f"Series {idx}: {field} must be string")
        # Allow empty category but not empty ticker or title
        if field != "category" and not series_data[field]:
            raise ValueError(f"Series {idx}: {field} cannot be empty")


def validate_series_optional_fields(series_data: Mapping[str, Any], idx: int) -> None:
    """Validate optional fields if present."""
    if "frequency" in series_data:
        if not isinstance(series_data["frequency"], str):
            raise TypeError(f"Series {idx}: frequency must be string, got: {type(series_data['frequency'])}")

    if "status" in series_data:
        if not isinstance(series_data["status"], str):
            raise TypeError(f"Series {idx}: status must be string, got: {type(series_data['status'])}")
        valid_statuses = ["active", "inactive", "closed"]
        if series_data["status"] not in valid_statuses:
            raise ValueError(f"Series {idx}: Invalid status '{series_data['status']}'. " f"Valid statuses: {valid_statuses}")
