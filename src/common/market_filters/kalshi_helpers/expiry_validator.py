"""Expiry validation helpers for Kalshi markets."""

from datetime import datetime
from typing import Any, Mapping, Optional

from .data_converters import decode_payload, parse_expiry_datetime


def parse_expiry(metadata: Mapping[str, Any]) -> tuple[Optional[str], Optional[datetime]]:
    """Parse expiry from metadata, returning raw string and parsed datetime."""
    expiry_raw = decode_payload(metadata.get("close_time")) or decode_payload(metadata.get("expiry"))
    if not expiry_raw:
        return None, None

    try:
        expiry_dt = parse_expiry_datetime(str(expiry_raw))
        return str(expiry_raw), expiry_dt
    except ValueError:
        return str(expiry_raw), None


def validate_expiry(expiry_dt: Optional[datetime], current_time: datetime) -> tuple[bool, Optional[str]]:
    """Validate expiry is in the future."""
    if expiry_dt is None:
        return False, "unparseable_expiry"

    if expiry_dt <= current_time:
        return False, "expired"

    return True, None
