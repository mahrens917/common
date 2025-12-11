"""Event response validation helpers."""

from typing import Any, Dict


def validate_event_wrapper(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate event wrapper structure and return event data."""
    if not response_data:
        raise ValueError("Empty response from event API")

    if "event" not in response_data:
        raise ValueError(f"Missing 'event' wrapper in response. " f"Available fields: {list(response_data.keys())}")

    event_data = response_data["event"]

    if not isinstance(event_data, dict):
        raise TypeError("Event data must be dict")

    return event_data


def validate_event_required_fields(event_data: Dict[str, Any]) -> None:
    """Validate event has all required fields."""
    required_fields = ["ticker", "title", "category", "series_ticker"]
    missing_fields = [field for field in required_fields if field not in event_data]

    if missing_fields:
        raise ValueError(f"Missing required fields in event: {missing_fields}. " f"Available fields: {list(event_data.keys())}")


def validate_event_string_fields(event_data: Dict[str, Any]) -> None:
    """Validate event string fields are non-empty strings."""
    required_fields = ["ticker", "title", "category", "series_ticker"]

    for field in required_fields:
        if not isinstance(event_data[field], str):
            raise TypeError(f"Event {field} must be string")
        if not event_data[field]:
            raise ValueError(f"Event {field} cannot be empty")


def validate_event_markets_field(event_data: Dict[str, Any]) -> bool:
    """
    Validate markets field in event data if present.

    Returns:
        True if markets field is present and valid, False if not present
    """
    if "markets" not in event_data:
        return False

    if not isinstance(event_data["markets"], list):
        raise TypeError("Event markets must be list")

    return True
