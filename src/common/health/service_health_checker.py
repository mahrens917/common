"""
Service health checking with single responsibility: "Is the service responding?"

Checks if services are actually functional by testing their responsiveness
through Redis status or other health endpoints.
"""

import logging
from typing import Dict, List, Optional

from ..redis_protocol.typing import RedisClient
from .service_health_checker_helpers import redis_status_checker
from .service_health_checker_helpers.batch_health_checker import check_all_service_health
from .service_health_types import (
    HEALTH_CHECK_ERRORS,
    ServiceHealth,
    ServiceHealthInfo,
)

logger = logging.getLogger(__name__)


def ensure_awaitable(func_or_coro):
    """Ensure a function or coroutine is awaitable."""
    from ..redis_protocol.typing import ensure_awaitable as _ensure_awaitable

    return _ensure_awaitable(func_or_coro)


class ServiceHealthChecker:
    """
    Single responsibility: Check if services are responding to requests.

    Tests actual service functionality, not just process existence.
    Uses Redis status updates and other health indicators.
    """

    def __init__(self):
        self._redis_client: Optional[RedisClient] = None

    async def _get_redis_client(self) -> RedisClient:
        """Get Redis client for health checks"""
        if self._redis_client is None:
            from ..redis_protocol.connection import get_redis_client

            self._redis_client = await get_redis_client()

        assert self._redis_client is not None
        return self._redis_client

    async def check_service_health(self, service_name: str) -> ServiceHealthInfo:
        """
        Check health of a specific service.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealthInfo with responsiveness status
        """
        try:
            redis_client = await self._get_redis_client()

            # Check Redis status for the service
            redis_health = await redis_status_checker.check_redis_status(service_name, redis_client)

            # For now, use Redis status as primary health indicator
            # Future: Add HTTP health endpoints, WebSocket ping, etc.

        except HEALTH_CHECK_ERRORS as e:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.exception(f"Error checking health for : ")
            return ServiceHealthInfo(health=ServiceHealth.UNKNOWN, error_message=str(e))
        else:
            return redis_health

    async def check_all_service_health(self, service_names: List[str]) -> Dict[str, ServiceHealthInfo]:
        """
        Check health for multiple services efficiently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealthInfo
        """
        return await check_all_service_health(service_names, self.check_service_health)

    async def ping_service(self, service_name: str) -> bool:
        """
        Simple ping test for a service.

        Args:
            service_name: Name of the service to ping

        Returns:
            True if service responds, False otherwise
        """
        try:
            health_info = await self.check_service_health(service_name)
        except HEALTH_CHECK_ERRORS:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.debug("Expected exception, returning default value")
            return False
        else:
            return health_info.health in (ServiceHealth.HEALTHY, ServiceHealth.DEGRADED)
