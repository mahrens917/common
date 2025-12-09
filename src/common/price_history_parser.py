"""
Price history data parsing utilities

Handles parsing of individual hash entries with time-range filtering
and data validation.
"""

import logging
from datetime import datetime
from typing import Tuple

logger = logging.getLogger(__name__)


class PriceHistoryParser:
    """
    Parses price history hash entries

    Validates and converts datetime strings and price values,
    filtering by time range and excluding invalid data.
    """

    @staticmethod
    def parse_hash_entry(
        datetime_str: str, price_str: str, start_time: datetime
    ) -> Tuple[int, float] | None:
        """
        Parse single hash entry and filter by time range

        Args:
            datetime_str: ISO format datetime string
            price_str: Price as string
            start_time: Start time for filtering

        Returns:
            Tuple of (timestamp, price) if valid and within range, None otherwise
        """
        try:
            # Parse ISO format datetime string (e.g., "2025-09-09T01:47:22+00:00")
            dt = datetime.fromisoformat(datetime_str)

            # Filter by time range (both are now timezone-aware)
            if dt >= start_time:
                # Convert to Unix timestamp for compatibility
                timestamp = int(dt.timestamp())
                price = float(price_str)

                # Filter out zero values for better chart visualization
                if price > 0:
                    return (timestamp, price)

        except (
            ValueError,
            TypeError,
        ):
            logger.warning(f"Skipping invalid entry {datetime_str}")

        return None
