"""Field validation, timestamp conversion, and option normalization for Redis messages."""

from __future__ import annotations

from typing import Any, Optional, Union

from common.exceptions import DataError
from common.time_helpers.timestamp_parser import parse_timestamp
from common.truthy import pick_if

# --- Field validation ---


def validate_required_field(hash_data: dict[str, Any], field_name: str, context: str = "") -> Any:
    """Validate that a required field exists in hash data.

    Raises RuntimeError if field is missing.
    """
    value = hash_data.get(field_name)
    if value is None:
        context_suffix = pick_if(context, lambda: f" in {context}", lambda: "")
        raise RuntimeError(f"FAIL-FAST: Missing required {field_name} field{context_suffix}. " f"Cannot proceed with empty {field_name}.")
    return value


def validate_float_field(hash_data: dict[str, Any], field_name: str, context: str = "") -> float:
    """Validate and convert a field to float.

    Raises RuntimeError if field is missing or cannot be converted.
    """
    value_str = validate_required_field(hash_data, field_name, context)
    try:
        return float(value_str)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid {field_name} value '{value_str}' - cannot convert to float") from exc


# --- Timestamp conversion ---


def parse_utc_timestamp(value: Union[str, int, float]) -> int:
    """Parse ISO-8601 timestamps or numeric seconds into epoch seconds.

    Raises DataError if timestamp cannot be parsed.
    """
    try:
        dt = parse_timestamp(value, allow_none=False)
        assert dt is not None
        return int(dt.timestamp())
    except (ValueError, TypeError) as e:
        raise DataError(f"FAIL-FAST: Invalid timestamp format '{value}'. Cannot parse timestamp: {e}") from e


def format_utc_timestamp(timestamp: Union[int, float]) -> str:
    """Format integer timestamp to ISO-8601 UTC string with Z suffix."""
    dt = parse_timestamp(timestamp, allow_none=False)
    assert dt is not None
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- Option normalization ---


def normalize_option_type(option_type: Optional[str], option_kind: Optional[str] = None) -> Optional[str]:
    """Normalize option type to standard format ('call' or 'put')."""
    candidate = option_type
    if not candidate:
        candidate = option_kind
    if not candidate:
        return None
    lowered = str(candidate).strip().lower()
    if lowered.startswith("c"):
        return "call"
    if lowered.startswith("p"):
        return "put"
    return None
