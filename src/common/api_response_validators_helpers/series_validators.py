"""Series-specific validation helpers."""

from typing import Any, Mapping


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
