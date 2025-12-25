"""HTTP-based health checking."""

import asyncio
import logging
import time
from typing import List

import aiohttp
from aiohttp import ClientError, ClientTimeout

from .types import HealthStatus, ServiceHealth

logger = logging.getLogger(__name__)

# Constants
_TEMP_MAX = 200


class HttpHealthChecker:
    """Checks service health via HTTP endpoints."""

    def __init__(self, health_timeout_seconds: int = 5):
        """
        Initialize HTTP health checker.

        Args:
            health_timeout_seconds: Timeout for HTTP health checks
        """
        self.health_timeout_seconds = health_timeout_seconds

    async def check_http_health(self, service_name: str, health_urls: List[str]) -> ServiceHealth:
        """
        Check service health via HTTP endpoint.

        Args:
            service_name: Name of the service
            health_urls: List of URLs to try for health checks

        Returns:
            ServiceHealth based on HTTP response
        """
        for url in health_urls:
            try:
                start_time = time.time()

                async with aiohttp.ClientSession() as session:
                    timeout = ClientTimeout(total=self.health_timeout_seconds)
                    async with session.get(url, timeout=timeout) as response:
                        response_time_ms = (time.time() - start_time) * 1000

                        if response.status == _TEMP_MAX:
                            return ServiceHealth(
                                service_name=service_name,
                                status=HealthStatus.HEALTHY,
                                response_time_ms=response_time_ms,
                            )
                        else:
                            return ServiceHealth(
                                service_name=service_name,
                                status=HealthStatus.UNHEALTHY,
                                response_time_ms=response_time_ms,
                                error_message=f"HTTP {response.status}",
                            )

            except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
                logger.warning("Transient network/connection failure")
                return ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    error_message="HTTP timeout",
                )
            except (  # policy_guard: allow-silent-handler
                ClientError,
                OSError,
                ValueError,
            ):
                return ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"HTTP error",
                )

        return ServiceHealth(
            service_name=service_name,
            status=HealthStatus.UNKNOWN,
            error_message="No HTTP endpoints available",
        )
