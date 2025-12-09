"""Log file-based health checking."""

import os
import time

from .activity_classifier import ActivityClassifier
from .types import HealthStatus, ServiceHealth


class LogHealthChecker:
    """Checks service health via log file timestamps."""

    def __init__(
        self,
        logs_directory: str,
        log_staleness_threshold_seconds: int,
        activity_classifier: ActivityClassifier,
    ):
        """
        Initialize log health checker.

        Args:
            logs_directory: Directory containing service log files
            log_staleness_threshold_seconds: Threshold for considering logs stale
            activity_classifier: Classifier for log activity levels
        """
        self.logs_directory = logs_directory
        self.log_staleness_threshold_seconds = log_staleness_threshold_seconds
        self.activity_classifier = activity_classifier

    async def check_log_health(self, service_name: str) -> ServiceHealth:
        """
        Check service health via log file timestamp with detailed activity classification.

        Args:
            service_name: Name of the service

        Returns:
            ServiceHealth based on log file activity with detailed status
        """
        log_file = os.path.join(self.logs_directory, f"{service_name}.log")

        try:
            if not os.path.exists(log_file):
                return ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    error_message="Log file not found",
                    activity_status="Missing",
                    seconds_since_last_log=None,
                )

            last_modified = os.path.getmtime(log_file)
            age_seconds = int(time.time() - last_modified)

            # Classify activity level and generate detailed status
            activity_status = self.activity_classifier.classify_log_activity(age_seconds)

            # Determine overall health status
            if age_seconds < self.log_staleness_threshold_seconds:
                status = HealthStatus.HEALTHY
                error_message = None
            else:
                status = HealthStatus.UNHEALTHY
                error_message = f"Log stale ({age_seconds}s old)"

            return ServiceHealth(
                service_name=service_name,
                status=status,
                last_log_update=last_modified,
                error_message=error_message,
                activity_status=activity_status,
                seconds_since_last_log=age_seconds,
            )

        except OSError:
            return ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                error_message=f"Log check error",
                activity_status="Unknown",
                seconds_since_last_log=None,
            )
