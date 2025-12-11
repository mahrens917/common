"""Build ServiceHealthResult objects."""

from dataclasses import dataclass

from ..health_types import OverallServiceStatus, ServiceHealthResult
from ..log_activity_monitor import LogActivity, LogActivityStatus
from ..process_health_monitor import ProcessHealthInfo, ProcessStatus
from ..service_health_checker import ServiceHealth, ServiceHealthInfo


@dataclass(frozen=True)
class HealthResultComponents:
    """Components needed to build a health result."""

    service_name: str
    overall_status: OverallServiceStatus
    process_info: ProcessHealthInfo
    log_activity: LogActivity
    service_health: ServiceHealthInfo
    status_emoji: str
    status_message: str
    detailed_message: str


class ResultBuilder:
    """Build ServiceHealthResult objects from component statuses."""

    @staticmethod
    def build_result(
        components: HealthResultComponents,
    ) -> ServiceHealthResult:
        """
        Build a ServiceHealthResult from component statuses.

        Args:
            components: All components needed to build the result

        Returns:
            Complete ServiceHealthResult
        """
        return ServiceHealthResult(
            service_name=components.service_name,
            overall_status=components.overall_status,
            process_info=components.process_info,
            log_activity=components.log_activity,
            service_health=components.service_health,
            status_emoji=components.status_emoji,
            status_message=components.status_message,
            detailed_message=components.detailed_message,
            memory_percent=components.process_info.memory_percent,
            log_age_seconds=components.log_activity.age_seconds,
        )

    @staticmethod
    def build_error_result(service_name: str, error: BaseException) -> ServiceHealthResult:
        """
        Build an error ServiceHealthResult.

        Args:
            service_name: Name of the service
            error: Exception that occurred

        Returns:
            ServiceHealthResult indicating error
        """
        return ServiceHealthResult(
            service_name=service_name,
            overall_status=OverallServiceStatus.ERROR,
            process_info=ProcessHealthInfo(status=ProcessStatus.NOT_FOUND),
            log_activity=LogActivity(status=LogActivityStatus.ERROR, error_message=str(error)),
            service_health=ServiceHealthInfo(health=ServiceHealth.UNKNOWN, error_message=str(error)),
            status_emoji="🔴",
            status_message="Error",
            detailed_message=f"Failed to check status",
        )
