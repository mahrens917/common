"""Dawn calculation helper for dawn reset service."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from ..time_utils import calculate_dawn_utc, get_current_utc

logger = logging.getLogger(__name__)


class DawnCalculator:
    """
    Calculates dawn times and determines if dawn boundary has been crossed.

    Handles local dawn calculation for weather stations and detects
    transitions across dawn reset boundaries.
    """

    def __init__(self, calculate_dawn_fn=calculate_dawn_utc):
        # Allow dependency injection (and test monkeypatching) of the dawn calculator
        self._calculate_dawn_utc = calculate_dawn_fn or calculate_dawn_utc

    def is_new_trading_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Check if we've crossed local dawn since the previous timestamp.

        Args:
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            previous_timestamp: Previous timestamp to check against
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            Tuple of (is_new_day, relevant_dawn_boundary)

        Raises:
            ValueError: If coordinates are invalid or timestamps cannot be parsed
        """
        if current_timestamp is None:
            current_timestamp = get_current_utc()

        # Calculate local dawn for the current day
        dawn_current = self._calculate_dawn_utc(latitude, longitude, current_timestamp)

        # IMPORTANT: Reset happens 1 minute BEFORE dawn to ensure clean state when trading opens
        dawn_reset_time = dawn_current - timedelta(minutes=1)

        # Also check dawn for the previous day in case we're right around dawn time
        previous_day = current_timestamp - timedelta(days=1)
        dawn_previous = self._calculate_dawn_utc(latitude, longitude, previous_day)
        dawn_reset_previous = dawn_previous - timedelta(minutes=1)

        # Determine which dawn boundary is relevant
        # Reset triggers 1 minute BEFORE dawn to ensure clean state
        is_new_day = False
        relevant_dawn = None

        if previous_timestamp < dawn_reset_previous and current_timestamp >= dawn_reset_previous:
            # Crossed yesterday's dawn reset time
            is_new_day = True
            relevant_dawn = dawn_reset_previous
        elif previous_timestamp < dawn_reset_time and current_timestamp >= dawn_reset_time:
            # Crossed today's dawn reset time
            is_new_day = True
            relevant_dawn = dawn_reset_time

        return is_new_day, relevant_dawn

    def resolve_latest_dawn_boundary(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """
        Determine the most recent dawn reset boundary relative to the current timestamp.

        Args:
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            Most recent dawn reset boundary datetime
        """
        if current_timestamp is None:
            current_timestamp = get_current_utc()

        dawn_current = self._calculate_dawn_utc(latitude, longitude, current_timestamp)
        dawn_reset_current = dawn_current - timedelta(minutes=1)

        if current_timestamp >= dawn_reset_current:
            return dawn_reset_current

        previous_day = current_timestamp - timedelta(days=1)
        dawn_previous = self._calculate_dawn_utc(latitude, longitude, previous_day)
        return dawn_previous - timedelta(minutes=1)
