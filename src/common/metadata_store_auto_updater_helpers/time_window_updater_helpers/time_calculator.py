"""Time window calculations."""

from datetime import datetime, timedelta
from typing import Tuple


def calculate_time_thresholds(current_time: datetime) -> Tuple[str, str, str]:
    """
    Calculate time thresholds for windowed counting.

    Args:
        current_time: Current datetime

    Returns:
        Tuple of (hour_ago, sixty_five_minutes_ago, sixty_seconds_ago) as ISO strings
    """
    hour_ago_str = (current_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    sixty_five_minutes_ago_str = (current_time - timedelta(minutes=65)).strftime("%Y-%m-%d %H:%M:%S")
    sixty_seconds_ago_str = (current_time - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
    return hour_ago_str, sixty_five_minutes_ago_str, sixty_seconds_ago_str
