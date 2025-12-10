"""
Service status printing helpers for OptimizedStatusReporter.

Extracted from OptimizedStatusReporter to reduce class size.
"""

from typing import Any, Dict, Optional, Tuple

from common.health.log_activity_monitor import LogActivity
from common.monitoring import ProcessStatus

from .status_line_builder import get_status_emoji, resolve_service_status


class ServicePrinter:
    """Handles printing of service status lines."""

    def __init__(self, emit_func, resource_tracker, log_formatter, bool_or_default_func):
        self._emit = emit_func
        self._resource_tracker = resource_tracker
        self._log_formatter = log_formatter
        self._bool_or_default = bool_or_default_func

    def print_managed_services(
        self,
        process_manager,
        tracker_status: Dict[str, Any],
        log_activity_map: Dict[str, LogActivity],
    ) -> Tuple[int, int]:
        healthy_count = 0
        total_count = 0

        for service_name in sorted(process_manager.services):
            info = process_manager.process_info.get(service_name)
            running = bool(info and info.status == ProcessStatus.RUNNING)
            activity = log_activity_map.get(service_name)

            service_line = self._build_service_status_line(
                service_name=service_name,
                info=info,
                running=running,
                tracker_status=tracker_status,
                activity=activity,
            )
            self._emit(service_line)

            total_count += 1
            if running:
                healthy_count += 1

        return healthy_count, total_count

    def print_monitor_service(
        self, process_manager, log_activity_map: Dict[str, LogActivity]
    ) -> None:
        monitor_info = process_manager.process_info.get("monitor")
        if not monitor_info:
            return

        running = monitor_info.status == ProcessStatus.RUNNING
        activity = log_activity_map.get("monitor")
        emoji = get_status_emoji(running, activity)

        if running:
            status_display = "Running"
        elif monitor_info.status:
            status_display = monitor_info.status.value.replace("_", " ").title()
        else:
            status_display = "Unknown"

        resource_info = self._resource_tracker.get_process_resource_usage("monitor")
        line = f"  {emoji} monitor - {status_display}"
        if resource_info:
            line += f" - {resource_info.strip()}"

        activity_summary = self._log_formatter.format_log_activity_short("monitor", activity)
        if activity_summary:
            line += f" - {activity_summary}"

        self._emit(line)

    def _build_service_status_line(
        self,
        service_name: str,
        info: Optional[Any],
        running: bool,
        tracker_status: Dict[str, Any],
        activity: Optional[LogActivity],
    ) -> str:
        emoji = get_status_emoji(running, activity)
        status_display = resolve_service_status(
            service_name, info, running, tracker_status, self._bool_or_default
        )

        # Get age information to append to status
        age_str = self._log_formatter.format_age_only(activity)
        if age_str:
            status_display = f"{status_display} ({age_str})"

        resource_info = self._resource_tracker.get_process_resource_usage(service_name)

        line = f"  {emoji} {service_name} - {status_display}"
        if resource_info:
            line += f"{resource_info}"

        return line
