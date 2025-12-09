"""
Simple Health Checker

A lightweight health checking system that uses HTTP endpoints and log file timestamps
instead of complex Redis-based state tracking. Designed to replace the complex
health monitoring infrastructure with a fail-fast, simple approach.
"""

import logging
from typing import Dict, List

from .simple_health_checker_helpers.simple_health_delegator import SimpleHealthDelegator
from .simple_health_checker_helpers.types import HealthStatus, ServiceHealth

logger = logging.getLogger(__name__)

DEFAULT_HEALTH_TIMEOUT_SECONDS = 5
DEFAULT_LOG_STALENESS_THRESHOLD_SECONDS = 300
DEFAULT_ACTIVE_THRESHOLD_SECONDS = 3600
DEFAULT_FRESH_THRESHOLD_SECONDS = 86400

__all__ = ["SimpleHealthChecker", "HealthStatus", "ServiceHealth"]


class SimpleHealthChecker:
    """
    Simple health checker that uses HTTP endpoints and log file timestamps.

    No Redis dependencies for process management - just checks if services
    are responding and logging activity.

    This is a slim coordinator that delegates all operations to specialized helpers.
    """

    def __init__(self, logs_directory: str = "./logs"):
        """
        Initialize health checker.

        Args:
            logs_directory: Directory containing service log files
        """
        self.logs_directory = logs_directory
        self.health_timeout_seconds = DEFAULT_HEALTH_TIMEOUT_SECONDS
        self.log_staleness_threshold_seconds = DEFAULT_LOG_STALENESS_THRESHOLD_SECONDS

        # Activity classification thresholds
        self.active_threshold_seconds = DEFAULT_ACTIVE_THRESHOLD_SECONDS
        self.fresh_threshold_seconds = DEFAULT_FRESH_THRESHOLD_SECONDS

        # Create delegator with all dependencies
        self._delegator = SimpleHealthDelegator(
            logs_directory=self.logs_directory,
            health_timeout_seconds=self.health_timeout_seconds,
            log_staleness_threshold_seconds=self.log_staleness_threshold_seconds,
            active_threshold_seconds=self.active_threshold_seconds,
            fresh_threshold_seconds=self.fresh_threshold_seconds,
        )

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """
        Check health of a specific service using the HTTP endpoint.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealth with status and details
        """
        return await self._delegator.check_service_health(service_name)

    async def check_multiple_services(self, service_names: List[str]) -> Dict[str, ServiceHealth]:
        """
        Check health for multiple services concurrently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealth
        """
        return await self._delegator.check_multiple_services(service_names)

    def is_service_healthy(self, service_health: ServiceHealth) -> bool:
        """
        Simple boolean check if service is healthy.

        Args:
            service_health: ServiceHealth object

        Returns:
            True if service is healthy, False otherwise
        """
        return self._delegator.is_service_healthy(service_health)

    async def get_detailed_service_status(self, service_name: str) -> ServiceHealth:
        """
        Get detailed service status with enhanced activity classification.
        This method prioritizes log activity analysis over HTTP checks for detailed status.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealth with detailed activity status information
        """
        return await self._delegator.get_detailed_service_status(service_name)
