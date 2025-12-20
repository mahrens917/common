"""Aggregate component statuses into overall status."""

from __future__ import annotations

from ..health_types import OverallServiceStatus
from ..log_activity_monitor import LogActivity, LogActivityStatus
from ..process_health_monitor import ProcessHealthInfo, ProcessStatus
from ..service_health_checker import ServiceHealth, ServiceHealthInfo
from .status_builder import StatusBuilder


class StatusAggregator:
    """Aggregate component statuses into overall status using clear decision logic."""

    def __init__(self):
        self.builder = StatusBuilder()

    def _check_process_status(self, process_info: ProcessHealthInfo) -> tuple[OverallServiceStatus, str, str, str] | None:
        """Check process status and return result if applicable."""
        if process_info.status == ProcessStatus.STOPPED:
            return (OverallServiceStatus.STOPPED, "🔴", "Stopped", "process: stopped")
        if process_info.status == ProcessStatus.NOT_FOUND:
            return (OverallServiceStatus.NOT_FOUND, "🔴", "Not Found", "process: not found")
        return None

    def _check_service_issues(
        self, service_health: ServiceHealthInfo, log_activity: LogActivity
    ) -> tuple[OverallServiceStatus, str, str, str] | None:
        """Check service health issues and return result if applicable."""
        if service_health.health == ServiceHealth.UNRESPONSIVE:
            return self.builder.build_unresponsive_status(log_activity)
        if service_health.health == ServiceHealth.DEGRADED:
            return self.builder.build_degraded_status(log_activity)
        return None

    def _check_log_issues(
        self, log_activity: LogActivity, service_health: ServiceHealthInfo
    ) -> tuple[OverallServiceStatus, str, str, str] | None:
        """Check log activity issues and return result if applicable."""
        if log_activity.status in (
            LogActivityStatus.OLD,
            LogActivityStatus.NOT_FOUND,
            LogActivityStatus.ERROR,
        ):
            return self.builder.build_silent_status_from_logs(log_activity, service_health)
        if log_activity.status == LogActivityStatus.STALE:
            return self.builder.build_silent_status_from_stale_logs(log_activity)
        return None

    def aggregate_status(
        self,
        service_name: str,
        process_info: ProcessHealthInfo,
        log_activity: LogActivity,
        service_health: ServiceHealthInfo,
    ) -> tuple[OverallServiceStatus, str, str, str]:
        """
        Aggregate component statuses into overall status.

        Args:
            service_name: Name of the service
            process_info: Process health information
            log_activity: Log activity information
            service_health: Service health information

        Returns:
            Tuple of (overall_status, emoji, status_message, detailed_message)
        """
        result = self._check_process_status(process_info)
        if result:
            return result

        result = self._check_service_issues(service_health, log_activity)
        if result:
            return result

        result = self._check_log_issues(log_activity, service_health)
        if result:
            return result

        if (
            process_info.status == ProcessStatus.RUNNING
            and log_activity.status == LogActivityStatus.RECENT
            and service_health.health in (ServiceHealth.HEALTHY, ServiceHealth.UNKNOWN)
        ):
            return self.builder.build_healthy_status(log_activity)

        return self.builder.build_error_status(process_info, log_activity, service_health)
