"""Monitor service status printing helper."""

from typing import Dict

from src.common.health.log_activity_monitor import LogActivity, LogActivityStatus
from src.common.monitoring import ProcessStatus


class MonitorServicePrinter:
    """Prints monitor service status."""

    def __init__(self, process_manager, service_status_formatter):
        self.process_manager = process_manager
        self.service_status_formatter = service_status_formatter

    def build_monitor_status_line(self, log_activity_map: Dict[str, LogActivity]) -> str:
        """Build monitor service status line."""
        monitor_info = self.process_manager.process_info.get("monitor")
        if not monitor_info:
            return ""

        running = monitor_info.status == ProcessStatus.RUNNING
        activity = log_activity_map.get("monitor")

        # Determine emoji
        if running:
            emoji = "🟢"
        else:
            emoji = "🔴"
        if running and activity and activity.status == LogActivityStatus.ERROR:
            emoji = "🟡"

        # Determine status display
        if running:
            status_display = "Active"
        elif monitor_info.status:
            status_display = monitor_info.status.value.replace("_", " ").title()
        else:
            status_display = "Unknown"

        # Get age information to append to status
        age_str = self.service_status_formatter.log_activity_formatter.format_age_only(activity)
        if age_str:
            status_display = f"{status_display} ({age_str})"

        # Build base line
        line = f"  {emoji} monitor - {status_display}"

        # Add resource info
        resource_info = self.service_status_formatter.resource_tracker.get_process_resource_usage(
            "monitor"
        )
        if resource_info:
            line += f"{resource_info}"

        return line
