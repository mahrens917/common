"""Dawn check coordinator for DawnResetService."""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from ..time_utils import calculate_dawn_utc


class DawnCheckCoordinator:
    """Coordinates dawn trading day checks with caching."""

    def __init__(self, dawn_calculator, cache_manager, logger):
        """Initialize dawn check coordinator."""
        self.dawn_calculator = dawn_calculator
        self.cache_manager = cache_manager
        self.logger = logger

    def check_new_trading_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: datetime,
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if we've crossed local dawn since the previous timestamp."""
        # Check cache
        cache_key = self.cache_manager.get_cache_key(latitude, longitude, previous_timestamp, current_timestamp)
        cached_result = self.cache_manager.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        # Calculate dawn times
        dawn_current = calculate_dawn_utc(latitude, longitude, current_timestamp)
        dawn_reset_time = dawn_current - timedelta(minutes=1)
        previous_day = current_timestamp - timedelta(days=1)
        dawn_previous = calculate_dawn_utc(latitude, longitude, previous_day)

        # Determine if new trading day
        result = self.dawn_calculator.is_new_trading_day(latitude, longitude, previous_timestamp, current_timestamp)

        # Log the check
        self.logger.log_dawn_check(
            latitude,
            longitude,
            previous_timestamp,
            current_timestamp,
            dawn_previous,
            dawn_current,
            dawn_reset_time,
            result[0],
            result[1],
            is_cached=False,
        )

        # Cache and return
        self.cache_manager.cache_result(cache_key, result)
        return result
