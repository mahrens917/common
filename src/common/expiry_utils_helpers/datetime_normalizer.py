"""Helpers for normalizing datetime objects."""

from datetime import datetime
from typing import Any

from ..time_helpers.expiry_conversions import parse_expiry_datetime


def parse_expiry_to_datetime(expiry_value: Any) -> datetime:
    """Parse expiry value to timezone-aware datetime via canonical helper."""
    return parse_expiry_datetime(expiry_value)
