"""Trading day check coordinator."""

from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from ..time_utils import calculate_dawn_utc
from .logger import DawnCheckContext


class TradingDayChecker:
    """Coordinates new trading day detection with caching and logging."""

    def __init__(self, dawn_calculator: Any, cache_manager: Any, logger: Any):
        self.dawn_calculator = dawn_calculator
        self.cache_manager = cache_manager
        self.logger = logger

    def is_new_trading_day(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if we've crossed into a new trading day at local dawn."""
        from ..time_utils import get_current_utc

        if current_timestamp is None:
            current_timestamp = get_current_utc()

        cache_key = self.cache_manager.get_cache_key(latitude, longitude, previous_timestamp, current_timestamp)
        cached_result = self.cache_manager.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        dawn_current = calculate_dawn_utc(latitude, longitude, current_timestamp)
        dawn_reset_time = dawn_current - timedelta(minutes=1)
        previous_day = current_timestamp - timedelta(days=1)
        dawn_previous = calculate_dawn_utc(latitude, longitude, previous_day)

        result = self.dawn_calculator.is_new_trading_day(latitude, longitude, previous_timestamp, current_timestamp)

        log_context = DawnCheckContext(
            latitude=latitude,
            longitude=longitude,
            previous_timestamp=previous_timestamp,
            current_timestamp=current_timestamp,
            dawn_previous=dawn_previous,
            dawn_current=dawn_current,
            dawn_reset_time=dawn_reset_time,
            is_new_day=result[0],
            relevant_dawn=result[1],
            is_cached=False,
        )
        self.logger.log_dawn_check(log_context)

        self.cache_manager.cache_result(cache_key, result)
        return result
