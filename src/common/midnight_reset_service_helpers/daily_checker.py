"""Checks if a new local day has begun based on midnight crossing."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..time_utils import calculate_local_midnight_utc

logger = logging.getLogger(__name__)


class DailyChecker:
    """Determines if local midnight has been crossed since previous timestamp."""

    def is_new_local_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Check if we've crossed local midnight since the previous timestamp.

        Args:
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            previous_timestamp: Previous timestamp to check against
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            True if local midnight has passed since previous_timestamp

        Raises:
            ValueError: If coordinates are invalid or timestamps cannot be parsed
        """
        if current_timestamp is None:
            from ..time_utils import get_current_utc

            current_timestamp = get_current_utc()

        # Calculate local midnight for the day AFTER the previous timestamp
        # This gives us the next midnight boundary that we need to cross
        next_day = previous_timestamp + timedelta(days=1)
        local_midnight = calculate_local_midnight_utc(latitude, longitude, next_day)

        # If current time is after the next local midnight since the previous timestamp,
        # we've crossed into a new local day
        is_new_day = current_timestamp >= local_midnight

        logger.info(f"🕛 MIDNIGHT RESET CHECK: lat={latitude}, lon={longitude}")
        logger.info(f"   Previous: {previous_timestamp.isoformat()}")
        logger.info(f"   Current:  {current_timestamp.isoformat()}")
        logger.info(f"   Local midnight boundary: {local_midnight.isoformat()}")
        logger.info(f"   ⏰ New local day: {is_new_day}")

        return is_new_day
