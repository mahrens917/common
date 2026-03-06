"""Health monitoring for REST connection managers."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from common.health.types import BaseHealthMonitor, HealthCheckResult

_HTTP_OK = 200


class RESTHealthMonitor(BaseHealthMonitor):
    """Monitors health of a REST endpoint via periodic GET requests."""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        health_path: str,
        session_manager: Any,
        logger_override: Any,
    ) -> None:
        super().__init__(service_name)
        self.base_url = base_url
        self.health_path = health_path
        self.session_manager = session_manager
        if logger_override is not None:
            self.logger = logger_override
        else:
            self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def check_health(self) -> HealthCheckResult:
        """Perform a GET request to the health endpoint and return the result."""
        session = self.session_manager.get_session()
        url = f"{self.base_url}{self.health_path}"
        with contextlib.suppress(asyncio.TimeoutError):
            async with session.get(url) as response:
                status = response.status
                if status == _HTTP_OK:
                    self.record_success()
                    return HealthCheckResult(True, details={"status": status}, error=None)
                self.record_failure()
                return HealthCheckResult(False, details={"status": status}, error=f"HTTP {status}")
        self.record_failure()
        return HealthCheckResult(False, error="timeout")


__all__ = ["RESTHealthMonitor"]
