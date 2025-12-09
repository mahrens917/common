"""
Log activity classification based on timestamp age.

Classifies log activity into states: RECENT, STALE, OLD based on
configurable thresholds.
"""

import logging
from datetime import datetime

from .types import LogActivityStatus

logger = logging.getLogger(__name__)


def classify_log_activity(
    last_timestamp: datetime,
    current_time: datetime,
    recent_threshold_seconds: int,
    stale_threshold_seconds: int,
) -> LogActivityStatus:
    """
    Classify log activity based on timestamp age.

    Thresholds define boundaries:
    - RECENT: age < recent_threshold_seconds
    - STALE: recent_threshold_seconds <= age < stale_threshold_seconds
    - OLD: age >= stale_threshold_seconds

    Args:
        last_timestamp: Timestamp of last log entry (timezone-aware)
        current_time: Current time for age calculation (timezone-aware)
        recent_threshold_seconds: Max age for RECENT status
        stale_threshold_seconds: Max age for STALE status

    Returns:
        LogActivityStatus (RECENT, STALE, or OLD)
    """
    age_seconds = (current_time - last_timestamp).total_seconds()

    if age_seconds < recent_threshold_seconds:
        return LogActivityStatus.RECENT
    elif age_seconds < stale_threshold_seconds:
        return LogActivityStatus.STALE
    else:
        return LogActivityStatus.OLD
