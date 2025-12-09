# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""Performance metric calculations."""

from typing import List

# Constants extracted for ruff PLR2004 compliance
AVG_REQUEST_TIME_SUCCESS_RATE_10 = 10
ELIF_AVG_REQUEST_TIME_0_7 = 0.7
ELIF_AVG_REQUEST_TIME_0_8 = 0.8


def calculate_performance_metrics(recent_metrics: List) -> tuple[float, float]:
    """
    Calculate average request time and success rate.

    Args:
        recent_metrics: List of NetworkMetrics

    Returns:
        Tuple of (avg_request_time, success_rate)
    """
    if not recent_metrics:
        return 0.0, 0.0

    avg_request_time = sum(m.request_time for m in recent_metrics) / len(recent_metrics)
    success_rate = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
    return avg_request_time, success_rate


def determine_new_interval(
    avg_request_time: float,
    success_rate: float,
    current_interval: int,
    min_interval: int,
    max_interval: int,
) -> int:
    """
    Determine new polling interval based on performance.

    Args:
        avg_request_time: Average request time in seconds
        success_rate: Success rate (0.0 to 1.0)
        current_interval: Current interval in seconds
        min_interval: Minimum allowed interval
        max_interval: Maximum allowed interval

    Returns:
        New interval in seconds
    """
    new_interval = current_interval

    # Fast, reliable network - poll more frequently
    if avg_request_time < 10 and success_rate > 0.9:
        new_interval = max(min_interval, current_interval - 5)
    # Slow/unreliable network - back off significantly
    elif avg_request_time > 30 or success_rate < 0.7:
        new_interval = min(max_interval, current_interval + 20)
    # Moderate performance issues - gentle backoff
    elif avg_request_time > 20 or success_rate < 0.8:
        new_interval = min(max_interval, current_interval + 10)

    return new_interval
