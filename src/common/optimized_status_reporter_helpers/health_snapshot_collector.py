"""
Health check snapshot aggregation.

Collects and categorizes system health checks.
"""

from typing import Any, Dict

from common.service_status import HealthStatus


class HealthSnapshotCollector:
    """Aggregates health check results."""

    def __init__(self, health_checker):
        self.health_checker = health_checker

    async def collect_health_snapshot(self) -> Dict[str, Any]:
        """Collect all health checks and extract key components."""
        health_checks = await self.health_checker.check_all_health()
        system_resources_health = None
        redis_health_check = None
        ldm_listener_health = None

        for check in health_checks:
            if check.name == "system_resources":
                system_resources_health = check
            elif check.name == "redis_connectivity":
                redis_health_check = check
            elif check.name == "ldm_listener":
                ldm_listener_health = check

        redis_connection_healthy = bool(redis_health_check and redis_health_check.status == HealthStatus.HEALTHY)

        return {
            "health_checks": health_checks,
            "system_resources_health": system_resources_health,
            "redis_health_check": redis_health_check,
            "ldm_listener_health": ldm_listener_health,
            "redis_connection_healthy": redis_connection_healthy,
        }
