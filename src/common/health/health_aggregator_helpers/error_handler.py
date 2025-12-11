"""Handle errors from component health checks."""

import logging

from ..log_activity_monitor import LogActivity, LogActivityStatus
from ..process_health_monitor import ProcessHealthInfo, ProcessStatus
from ..service_health_checker import ServiceHealth, ServiceHealthInfo

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handle exceptions from component health checks."""

    @staticmethod
    def ensure_process_info(service_name: str, result: ProcessHealthInfo | BaseException) -> ProcessHealthInfo:
        """
        Ensure process check result is valid.

        Args:
            service_name: Name of the service
            result: Result from process check or exception

        Returns:
            Valid ProcessHealthInfo
        """
        if isinstance(result, ProcessHealthInfo):
            return result
        logger.error(f"Process check failed for {service_name}: {result}")
        return ProcessHealthInfo(status=ProcessStatus.NOT_FOUND)

    @staticmethod
    def ensure_log_activity(service_name: str, result: LogActivity | BaseException) -> LogActivity:
        """
        Ensure log activity result is valid.

        Args:
            service_name: Name of the service
            result: Result from log check or exception

        Returns:
            Valid LogActivity
        """
        if isinstance(result, LogActivity):
            return result
        logger.error(f"Log check failed for {service_name}: {result}")
        return LogActivity(status=LogActivityStatus.ERROR, error_message=str(result))

    @staticmethod
    def ensure_service_health(service_name: str, result: ServiceHealthInfo | BaseException) -> ServiceHealthInfo:
        """
        Ensure service health result is valid.

        Args:
            service_name: Name of the service
            result: Result from health check or exception

        Returns:
            Valid ServiceHealthInfo
        """
        if isinstance(result, ServiceHealthInfo):
            return result
        logger.error(f"Health check failed for {service_name}: {result}")
        return ServiceHealthInfo(health=ServiceHealth.UNKNOWN, error_message=str(result))
