"""
Log activity monitoring with single responsibility: "When was the last meaningful log entry?"

Slim coordinator that delegates to helper modules:
- types: Shared enums and dataclasses
- log_file_finder: Locates most recent log files (handles rotation)
- timestamp_extractor: Extracts timestamps from log files
- activity_classifier: Classifies log activity status based on age
"""

import logging
from typing import Dict, List

from common.config import env_int

from .log_activity_monitor_helpers import (
    LogActivity,
    LogActivityStatus,
    classify_log_activity,
    extract_last_log_timestamp,
    find_most_recent_log_file,
)

logger = logging.getLogger(__name__)

LOG_ACTIVITY_ERRORS = (OSError, ValueError, RuntimeError, TypeError)


class LogActivityMonitor:
    """Single responsibility: Extract timestamps from log files."""

    def __init__(self, logs_directory: str = "./logs"):
        self.logs_directory = logs_directory
        self.recent_threshold_seconds = env_int("LOG_RECENT_THRESHOLD", or_value=60) or 60
        self.stale_threshold_seconds = env_int("LOG_STALE_THRESHOLD", or_value=900) or 900

    def _find_most_recent_log_file(self, log_pattern: str):
        """Locate the most recent log file for the pattern."""
        return find_most_recent_log_file(self.logs_directory, log_pattern)

    def _get_last_log_timestamp(self, log_file_path: str):
        """Extract the timestamp from the log file."""
        return extract_last_log_timestamp(log_file_path)

    async def get_log_activity(self, service_name: str) -> LogActivity:
        log_pattern = f"{service_name}.log"
        try:
            log_file_path = self._find_most_recent_log_file(log_pattern)
            if not log_file_path:
                return LogActivity(
                    status=LogActivityStatus.NOT_FOUND,
                    error_message=f"No log file found for pattern: {log_pattern}",
                )
            last_timestamp = self._get_last_log_timestamp(log_file_path)
            if not last_timestamp:
                return LogActivity(
                    status=LogActivityStatus.ERROR,
                    log_file_path=log_file_path,
                    error_message="Could not parse timestamp from log file",
                )
            from ..time_utils import ensure_timezone_aware, get_current_utc

            last_timestamp_aware = ensure_timezone_aware(last_timestamp)
            now = get_current_utc()
            age_seconds = (now - last_timestamp_aware).total_seconds()
            status = classify_log_activity(
                last_timestamp_aware,
                now,
                self.recent_threshold_seconds,
                self.stale_threshold_seconds,
            )
            return LogActivity(
                status=status,
                last_timestamp=last_timestamp_aware,
                age_seconds=age_seconds,
                log_file_path=log_file_path,
            )
        except LOG_ACTIVITY_ERRORS as exc:
            logger.exception("Error checking log activity for %s", service_name)
            return LogActivity(status=LogActivityStatus.ERROR, error_message=str(exc))

    async def get_all_service_log_activity(
        self, service_names: List[str]
    ) -> Dict[str, LogActivity]:
        results = {}
        for service_name in service_names:
            results[service_name] = await self.get_log_activity(service_name)
        return results
