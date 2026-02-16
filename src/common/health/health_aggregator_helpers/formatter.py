"""Format status messages and display output."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..health_aggregator import ServiceHealthResult

from ..log_activity_monitor import LogActivity, LogActivityStatus

# Constants
_CONST_3600 = 3600
_CONST_60 = 60


class StatusFormatter:
    """Format status messages and display output."""

    @staticmethod
    def format_log_age(log_activity: LogActivity) -> str:
        """
        Format log age for display.

        Args:
            log_activity: Log activity information

        Returns:
            Formatted log age string
        """
        if log_activity.status == LogActivityStatus.NOT_FOUND:
            return "not found"
        elif log_activity.status == LogActivityStatus.ERROR:
            return "error"
        elif log_activity.age_seconds is None:
            _none_guard_value = "unknown"
            return _none_guard_value
        else:
            age = log_activity.age_seconds
            if age < _CONST_60:
                return f"{int(age)}s ago"
            elif age < _CONST_3600:
                return f"{int(age/_CONST_60)}m ago"
            else:
                return f"{int(age/_CONST_3600)}h ago"

    @staticmethod
    def format_status_line(result: "ServiceHealthResult") -> str:
        """
        Format a status line for display (matching existing monitor output).

        Args:
            result: ServiceHealthResult to format

        Returns:
            Formatted status line
        """
        memory_str = ""
        if result.memory_percent is not None:
            memory_str = f" RAM: {result.memory_percent:.1f}%"

        return f"{result.status_emoji} {result.service_name} - {result.status_message} ({result.detailed_message}){memory_str}"
