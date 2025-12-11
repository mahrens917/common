"""Build status tuples from component information."""

from ..health_types import OverallServiceStatus
from ..log_activity_monitor import LogActivity
from ..process_health_monitor import ProcessHealthInfo
from ..service_health_checker import ServiceHealth, ServiceHealthInfo
from .formatter import StatusFormatter


class StatusBuilder:
    """Build status tuples from component information."""

    def __init__(self):
        self.formatter = StatusFormatter()

    def build_unresponsive_status(self, log_activity: LogActivity) -> tuple[OverallServiceStatus, str, str, str]:
        """Build status for unresponsive service."""
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.UNRESPONSIVE,
            "🔴",
            "Unresponsive",
            f"process: running, logs: {log_msg}, health: unresponsive",
        )

    def build_silent_status_from_logs(
        self, log_activity: LogActivity, service_health: ServiceHealthInfo
    ) -> tuple[OverallServiceStatus, str, str, str]:
        """Build silent status from log activity problems."""
        if service_health.health == ServiceHealth.HEALTHY:
            health_msg = "responding"
        else:
            health_msg = service_health.health.value
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.SILENT,
            "🟡",
            "Silent",
            f"process: running, logs: {log_msg}, health: {health_msg}",
        )

    def build_degraded_status(self, log_activity: LogActivity) -> tuple[OverallServiceStatus, str, str, str]:
        """Build status for degraded service."""
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.DEGRADED,
            "🟡",
            "Degraded",
            f"process: running, logs: {log_msg}, health: degraded",
        )

    def build_silent_status_from_stale_logs(self, log_activity: LogActivity) -> tuple[OverallServiceStatus, str, str, str]:
        """Build silent status from stale logs."""
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.SILENT,
            "🟡",
            "Silent",
            f"process: running, logs: {log_msg}, health: responding",
        )

    def build_healthy_status(self, log_activity: LogActivity) -> tuple[OverallServiceStatus, str, str, str]:
        """Build status for healthy service."""
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.HEALTHY,
            "🟢",
            "Healthy",
            f"process: running, logs: {log_msg}, health: responding",
        )

    def build_error_status(
        self,
        process_info: ProcessHealthInfo,
        log_activity: LogActivity,
        service_health: ServiceHealthInfo,
    ) -> tuple[OverallServiceStatus, str, str, str]:
        """Build status for unknown error."""
        log_msg = self.formatter.format_log_age(log_activity)
        return (
            OverallServiceStatus.ERROR,
            "🔴",
            "Unknown",
            f"process: {process_info.status.value}, logs: {log_msg}, health: {service_health.health.value}",
        )
