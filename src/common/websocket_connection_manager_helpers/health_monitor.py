"""WebSocket health monitoring."""

from __future__ import annotations

import asyncio
import logging

from websockets import WebSocketException

from common.truthy import pick_if

from ..health.types import BaseHealthMonitor, HealthCheckResult

DEFAULT_WEBSOCKET_PING_INTERVAL_SECONDS = 30
DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS = 10


class WebSocketHealthMonitor(BaseHealthMonitor):
    """Monitors WebSocket connection health."""

    def __init__(self, service_name: str, connection_provider):
        super().__init__(service_name)
        self.connection_provider = connection_provider
        self.ping_interval_seconds = DEFAULT_WEBSOCKET_PING_INTERVAL_SECONDS
        self.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS
        self.last_ping_time = 0.0
        self.last_pong_time = 0.0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def _validate_websocket_connection(self, websocket) -> tuple[bool, str | None]:
        """Validate websocket connection is usable."""
        if not websocket:
            self.logger.warning("WebSocket connection is None")
            return False, "connection_missing"

        if websocket.close_code is not None:
            self.logger.warning(f"WebSocket is closed (code: {websocket.close_code})")
            return False, "connection_closed"

        return True, None

    async def _perform_ping_check(self, websocket, current_time: float) -> tuple[bool, str | None]:
        """Perform ping/pong check if interval elapsed."""
        if current_time - self.last_ping_time >= self.ping_interval_seconds:
            self.logger.debug("Sending ping")
            pong_waiter = await websocket.ping()

            try:
                await asyncio.wait_for(pong_waiter, timeout=self.pong_timeout_seconds)
                self.last_ping_time = current_time
                self.last_pong_time = current_time
                self.logger.debug("Received pong")
            except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
                self.logger.warning("Pong timeout")
                return False, "pong_timeout"
            else:
                return True, None

        time_since_last_pong = current_time - self.last_pong_time
        if time_since_last_pong > (self.ping_interval_seconds * 2):
            self.logger.warning(f"No pong received for {time_since_last_pong:.1f}s")
            return False, "pong_stale"

        return True, None

    async def check_health(self) -> HealthCheckResult:
        """Check WebSocket health using ping/pong."""
        websocket = self.connection_provider.get_connection()
        valid, connection_error = self._validate_websocket_connection(websocket)
        if not valid:
            self.record_failure()
            details = pick_if(websocket, lambda: {"close_code": getattr(websocket, "close_code", None)}, lambda: None)
            return HealthCheckResult(False, details=details, error=connection_error)

        try:
            loop = asyncio.get_running_loop()
            current_time = loop.time()
            healthy, error = await self._perform_ping_check(websocket, current_time)
            if healthy:
                self.record_success(timestamp=current_time)
                return HealthCheckResult(
                    True,
                    details={
                        "last_ping_time": self.last_ping_time,
                        "last_pong_time": self.last_pong_time,
                    },
                )

            self.record_failure()
            return HealthCheckResult(
                False,
                details={
                    "last_ping_time": self.last_ping_time,
                    "last_pong_time": self.last_pong_time,
                },
                error=error,
            )
        except WebSocketException as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
            self.logger.warning("WebSocket health check failed")
            self.record_failure()
            return HealthCheckResult(False, error=str(exc))
        except (OSError, RuntimeError) as exc:  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            self.logger.exception("Unexpected health check error: ")
            self.record_failure()
            return HealthCheckResult(False, error=str(exc))

    def initialize_pong_time(self) -> None:
        """Initialize pong tracking."""
        loop = asyncio.get_running_loop()
        self.last_ping_time = 0.0
        self.last_pong_time = loop.time()
