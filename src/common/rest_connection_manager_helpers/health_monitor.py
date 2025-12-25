"""REST health monitoring."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from ..health.types import BaseHealthMonitor, HealthCheckResult

# Constants
_CONST_400 = 400
_TEMP_MAX = 200


class RESTHealthMonitor(BaseHealthMonitor):
    """Monitors REST API health."""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        health_check_endpoint: str,
        session_manager,
        auth_handler,
    ):
        super().__init__(service_name)
        self.base_url = base_url
        self.health_check_endpoint = health_check_endpoint
        self.session_manager = session_manager
        self.auth_handler = auth_handler
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def check_health(self) -> HealthCheckResult:
        """Check REST API health."""
        session = self.session_manager.get_session()
        if not session:
            self.logger.warning("HTTP session is closed")
            self.record_failure()
            return HealthCheckResult(False, error="session_closed")

        try:
            health_url = f"{self.base_url}{self.health_check_endpoint}"
            self.logger.debug(f"Performing health check: {health_url}")

            kwargs = {}
            if self.auth_handler:
                try:
                    auth_headers = self.auth_handler("GET", self.health_check_endpoint)
                except TypeError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                    auth_headers = self.auth_handler()

                if auth_headers:
                    kwargs["headers"] = auth_headers

            health_timeout = aiohttp.ClientTimeout(total=10.0)

            async with session.get(health_url, timeout=health_timeout, **kwargs) as response:
                if _TEMP_MAX <= response.status < _CONST_400:
                    self.logger.debug(f"Health check passed: {response.status}")
                    self.record_success()
                    return HealthCheckResult(True, details={"status": response.status})

                self.logger.warning(f"Health check failed: HTTP {response.status}")
                self.record_failure()
                return HealthCheckResult(
                    False,
                    details={"status": response.status},
                    error=f"HTTP {response.status}",
                )

        except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
            self.logger.warning("Health check timeout")
            self.record_failure()
            return HealthCheckResult(False, error="timeout")
        except aiohttp.ClientError as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
            self.logger.warning("Health check client error")
            self.record_failure()
            return HealthCheckResult(False, error=str(exc))
        except OSError as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            self.logger.exception("Unexpected error in health check: ")
            self.record_failure()
            return HealthCheckResult(False, error=str(exc))
