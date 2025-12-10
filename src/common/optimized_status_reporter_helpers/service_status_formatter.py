"""
Service status line formatting.

Builds status display lines for individual services.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

from common.monitoring import ProcessStatus

if TYPE_CHECKING:
    from common.health.log_activity_monitor_helpers.types import LogActivity
    from common.monitoring.process_models import ProcessInfo


class ServiceStatusFormatter:
    """Formats service status lines for console display."""

    def __init__(self, resource_tracker, log_activity_formatter):
        self.resource_tracker = resource_tracker
        self.log_activity_formatter = log_activity_formatter

    def build_service_status_line(
        self,
        service_name: str,
        info: Optional["ProcessInfo"],
        running: bool,
        tracker_status: Dict[str, Any],
        activity: Optional["LogActivity"],
    ) -> str:
        """Build complete status line for a service."""
        from common.health.log_activity_monitor import LogActivityStatus

        if running:
            emoji = "🟢"
        else:
            emoji = "🔴"
        if running and activity and activity.status == LogActivityStatus.ERROR:
            emoji = "🟡"

        status_display = self._resolve_service_status(service_name, info, running, tracker_status)

        # Get age information to append to status
        age_str = self.log_activity_formatter.format_age_only(activity)
        if age_str:
            status_display = f"{status_display} ({age_str})"

        resource_info = self.resource_tracker.get_process_resource_usage(service_name)

        line = f"  {emoji} {service_name} - {status_display}"
        if resource_info:
            line += f"{resource_info}"

        return line

    @staticmethod
    def _resolve_tracker_specific_status(running: bool, tracker_status: Dict[str, Any]) -> str:
        """Determine status display text specifically for tracker service."""
        # Tracker enabled is True if not explicitly set to False
        enabled_raw = tracker_status.get("enabled")
        enabled = enabled_raw if enabled_raw is not None else True
        tracker_status["running"] = running
        if running:
            return "Active"
        if not enabled:
            return "Disabled"
        return "Stopped"

    @staticmethod
    def _resolve_service_status(
        service_name: str,
        info: Optional["ProcessInfo"],
        running: bool,
        tracker_status: Dict[str, Any],
    ) -> str:
        """Determine status display text for service."""
        if service_name == "tracker":
            return ServiceStatusFormatter._resolve_tracker_specific_status(running, tracker_status)

        if not info:
            return "Unknown"

        if running:
            return "Active"
        if info.status == ProcessStatus.STOPPED:
            return "Stopped"
        return info.status.value.replace("_", " ").title()
