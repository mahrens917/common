"""Close time parsing utilities for ExpiryChecker."""

import logging
from datetime import datetime
from typing import Any, Optional

from ....market_filters.kalshi import parse_expiry_datetime

logger = logging.getLogger(__name__)


class CloseTimeParser:
    """Parses and validates close_time fields from market data."""

    @staticmethod
    def parse_close_time_from_field(close_time_raw: Any) -> Optional[datetime]:
        """Parse close_time from Redis field value."""
        close_time = ""
        if isinstance(close_time_raw, bytes):
            close_time = close_time_raw.decode("utf-8")
        elif isinstance(close_time_raw, str):
            close_time = close_time_raw

        if not close_time:
            return None

        try:
            return parse_expiry_datetime(close_time)
        except (ValueError, TypeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning(f"Error parsing close_time '{close_time}': {exc}")
            return None

    @staticmethod
    def decode_close_time_string(raw_close_time: Any) -> str:
        """Decode close_time to string format."""
        if isinstance(raw_close_time, bytes):
            return raw_close_time.decode("utf-8")
        elif isinstance(raw_close_time, str):
            return raw_close_time
        return ""
