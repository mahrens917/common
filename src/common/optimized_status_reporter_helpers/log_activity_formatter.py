"""
Log activity formatting for status display.

Formats log activity status into condensed inline summaries.
"""

import os
from typing import List, Optional

from src.common.health.log_activity_monitor import LogActivity, LogActivityStatus


class LogActivityFormatter:
    """Formats log activity for status lines."""

    def __init__(self, time_formatter):
        self.time_formatter = time_formatter

    def format_log_activity_short(
        self, service_name: str, activity: Optional[LogActivity]
    ) -> Optional[str]:
        """Condensed log activity summary for inline status lines."""
        if not activity:
            return None

        status_label = activity.status.value.replace("_", " ").title()
        details: List[str] = []

        if activity.age_seconds is not None and activity.age_seconds >= 0:
            details.append(f"{self.time_formatter.humanize_duration(activity.age_seconds)} ago")

        if activity.status == LogActivityStatus.NOT_FOUND and activity.log_file_path:
            details.append(f"expected {os.path.basename(activity.log_file_path)}")
        elif activity.status == LogActivityStatus.ERROR and activity.error_message:
            details.append(activity.error_message)

        if details:
            return f"{status_label} ({', '.join(details)})"
        return status_label

    def format_age_only(self, activity: Optional[LogActivity]) -> Optional[str]:
        """Format just the age portion (e.g., '5s old') for inline status display."""
        if not activity or activity.age_seconds is None or activity.age_seconds < 0:
            return None
        return f"{self.time_formatter.humanize_duration(activity.age_seconds)} old"
