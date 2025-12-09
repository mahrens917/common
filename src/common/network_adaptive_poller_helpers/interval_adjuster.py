"""Interval adjustment logic for NetworkAdaptivePoller."""

import logging
from typing import List

logger = logging.getLogger(__name__)


# Constants
_CONST_0_7 = 0.7
_CONST_0_8 = 0.8
_CONST_0_9 = 0.9
_CONST_10 = 10
_CONST_20 = 20
_CONST_3 = 3
_CONST_30 = 30


class IntervalAdjuster:
    """Adjusts polling interval based on network performance metrics."""

    @staticmethod
    def calculate_adjusted_interval(
        recent_metrics: List,
        current_interval: int,
        min_interval: int,
        max_interval: int,
    ) -> int:
        """Calculate new polling interval based on recent performance.

        Args:
            recent_metrics: List of recent NetworkMetrics
            current_interval: Current polling interval
            min_interval: Minimum allowed interval
            max_interval: Maximum allowed interval

        Returns:
            New polling interval in seconds
        """
        if len(recent_metrics) < _CONST_3:
            return current_interval

        # Calculate performance metrics
        avg_request_time = sum(m.request_time for m in recent_metrics) / len(recent_metrics)
        success_rate = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)

        new_interval = _apply_interval_rules(
            avg_request_time,
            success_rate,
            current_interval,
            min_interval,
            max_interval,
        )

        # Log interval changes
        if new_interval != current_interval:
            logger.info(
                f"📊 Adaptive polling interval: {current_interval}s → {new_interval}s "
                f"(avg_time={avg_request_time:.1f}s, success_rate={success_rate:.1%})"
            )

        return new_interval


def _apply_interval_rules(
    avg_request_time: float,
    success_rate: float,
    current_interval: int,
    min_interval: int,
    max_interval: int,
) -> int:
    for condition, adjustment in _INTERVAL_RULES:
        if condition(avg_request_time, success_rate):
            return adjustment(current_interval, min_interval, max_interval)
    return current_interval


_INTERVAL_RULES = (
    (
        lambda avg_time, success: avg_time < _CONST_10 and success > _CONST_0_9,
        lambda current, min_interval, _max: max(min_interval, current - 5),
    ),
    (
        lambda avg_time, success: avg_time > _CONST_30 or success < _CONST_0_7,
        lambda current, _min, max_interval: min(max_interval, current + _CONST_20),
    ),
    (
        lambda avg_time, success: avg_time > _CONST_20 or success < _CONST_0_8,
        lambda current, _min, max_interval: min(max_interval, current + _CONST_10),
    ),
)
