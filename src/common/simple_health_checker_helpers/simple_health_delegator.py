"""Delegator for coordinating health check operations."""

from typing import Dict, List

from .activity_classifier import ActivityClassifier
from .health_url_provider import HealthUrlProvider
from .http_health_checker import HttpHealthChecker
from .log_health_checker import LogHealthChecker
from .multi_service_checker import MultiServiceChecker
from .types import HealthStatus, ServiceHealth


class SimpleHealthDelegator:
    """Coordinates health check operations by delegating to specialized helpers."""

    def __init__(
        self,
        logs_directory: str,
        health_timeout_seconds: int,
        log_staleness_threshold_seconds: int,
        active_threshold_seconds: int,
        fresh_threshold_seconds: int,
    ):
        """
        Initialize health check delegator.

        Args:
            logs_directory: Directory containing service log files
            health_timeout_seconds: Timeout for HTTP health checks
            log_staleness_threshold_seconds: Threshold for considering logs stale
            active_threshold_seconds: Threshold for "active" classification
            fresh_threshold_seconds: Threshold for "fresh" classification
        """
        # Create specialized helpers
        self.activity_classifier = ActivityClassifier(
            active_threshold_seconds=active_threshold_seconds,
            fresh_threshold_seconds=fresh_threshold_seconds,
        )
        self.health_url_provider = HealthUrlProvider()
        self.http_health_checker = HttpHealthChecker(health_timeout_seconds=health_timeout_seconds)
        self.log_health_checker = LogHealthChecker(
            logs_directory=logs_directory,
            log_staleness_threshold_seconds=log_staleness_threshold_seconds,
            activity_classifier=self.activity_classifier,
        )
        self.multi_service_checker = MultiServiceChecker(check_service_health_fn=self.check_service_health)

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """
        Check health of a specific service using the HTTP endpoint.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealth with status and details
        """
        health_urls = self.health_url_provider.get_health_urls(service_name)
        http_health = await self.http_health_checker.check_http_health(service_name, health_urls)
        if http_health.status == HealthStatus.HEALTHY:
            return http_health

        return http_health

    async def check_multiple_services(self, service_names: List[str]) -> Dict[str, ServiceHealth]:
        """
        Check health for multiple services concurrently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealth
        """
        return await self.multi_service_checker.check_multiple_services(service_names)

    def is_service_healthy(self, service_health: ServiceHealth) -> bool:
        """
        Simple boolean check if service is healthy.

        Args:
            service_health: ServiceHealth object

        Returns:
            True if service is healthy, False otherwise
        """
        return service_health.status == HealthStatus.HEALTHY

    async def get_detailed_service_status(self, service_name: str) -> ServiceHealth:
        """
        Get detailed service status with enhanced activity classification.
        This method prioritizes log activity analysis over HTTP checks for detailed status.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealth with detailed activity status information
        """
        # For detailed status, prioritize log analysis
        log_health = await self.log_health_checker.check_log_health(service_name)

        # If log health is available, use it as primary source
        if log_health.status == HealthStatus.UNKNOWN:
            raise RuntimeError(f"Log health analysis unavailable for service {service_name}")

        return log_health
