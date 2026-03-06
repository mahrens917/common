"""WebSocket health monitoring via ping/pong."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from websockets import WebSocketException

from common.health.types import BaseHealthMonitor, HealthCheckResult

_DEFAULT_PING_INTERVAL = 30.0
_DEFAULT_PONG_TIMEOUT = 10.0


class WebSocketHealthMonitor(BaseHealthMonitor):
    """Monitors WebSocket health by sending periodic pings and tracking pong responses."""

    def __init__(self, service_name: str, connection_provider: Any) -> None:
        super().__init__(service_name)
        self._connection_provider = connection_provider
        self.ping_interval_seconds: float = _DEFAULT_PING_INTERVAL
        self.pong_timeout_seconds: float = _DEFAULT_PONG_TIMEOUT
        self.last_ping_time: float = 0.0
        self.last_pong_time: float = 0.0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def check_health(self) -> HealthCheckResult:
        """Check WebSocket health; returns a HealthCheckResult."""
        ws = self._connection_provider.get_connection()

        if ws is None:
            self.record_failure()
            return HealthCheckResult(False, error="connection_missing")

        if getattr(ws, "close_code", None) is not None:
            self.record_failure()
            return HealthCheckResult(False, error="connection_closed")

        loop = asyncio.get_running_loop()
        current_time = loop.time()

        if current_time - self.last_ping_time < self.ping_interval_seconds:
            return self._evaluate_recent_ping(current_time)

        return await self._send_ping(ws, current_time)

    def _evaluate_recent_ping(self, current_time: float) -> HealthCheckResult:
        """Evaluate health when no new ping is needed."""
        if self.last_pong_time < self.last_ping_time:
            self.record_failure()
            return HealthCheckResult(False, error="pong_stale")
        self.record_success(timestamp=current_time)
        return HealthCheckResult(True)

    async def _send_ping(self, ws: Any, current_time: float) -> HealthCheckResult:
        """Send a ping and await the pong response."""
        self.last_ping_time = current_time
        with contextlib.suppress(asyncio.TimeoutError, WebSocketException, OSError):
            pong_waiter = await ws.ping()
            await asyncio.wait_for(pong_waiter, timeout=self.pong_timeout_seconds)
            self.last_pong_time = current_time
            self.record_success(timestamp=current_time)
            return HealthCheckResult(True)
        self.record_failure()
        return HealthCheckResult(False, error="ping_failed")


__all__ = ["WebSocketHealthMonitor"]
