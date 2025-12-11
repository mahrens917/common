"""
WebSocket connection manager for unified WebSocket service management.

This module provides WebSocket-specific connection management that extends
the base connection manager with WebSocket-specific health checks, connection
establishment, and cleanup procedures.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import websockets

from .connection_manager import BaseConnectionManager
from .health.types import HealthCheckResult
from .websocket_connection_manager_helpers import (
    WebSocketConnectionLifecycle,
    WebSocketHealthMonitor,
    WebSocketMessageOperations,
)

if TYPE_CHECKING:
    # monitor.alerter is optional external dependency
    try:
        from monitor.alerter import Alerter
    except ImportError:
        Alerter = Any  # type: ignore[misc,assignment]

DEFAULT_WEBSOCKET_PING_INTERVAL_SECONDS = 30
DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS = 10


class WebSocketConnectionManager(BaseConnectionManager):
    def __init__(
        self,
        service_name: str,
        websocket_url: str,
        connection_factory: Optional[Callable] = None,
        alerter: Optional["Alerter"] = None,
    ):
        super().__init__(service_name, alerter)

        self.websocket_url = websocket_url

        factory = connection_factory or websockets.connect

        self.lifecycle_manager = WebSocketConnectionLifecycle(
            service_name,
            websocket_url,
            self.config.connection_timeout_seconds,
            factory,
        )

        self.health_monitor = WebSocketHealthMonitor(service_name, self.lifecycle_manager)

        self.message_ops = WebSocketMessageOperations(service_name, self.lifecycle_manager)

        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Default timing configuration - delegate to health monitor
        self.health_monitor.ping_interval_seconds = DEFAULT_WEBSOCKET_PING_INTERVAL_SECONDS
        self.health_monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS
        self.health_monitor.last_ping_time = 0.0
        self.health_monitor.last_pong_time = 0.0

    async def establish_connection(self) -> bool:
        try:
            result = await self.lifecycle_manager.establish_connection()
        except asyncio.CancelledError:
            raise
        except (OSError, ConnectionError, RuntimeError, ValueError):
            await self.cleanup_connection()
            raise
        if result:
            self.health_monitor.initialize_pong_time()
        return result

    async def check_connection_health(self) -> HealthCheckResult:
        """Check WebSocket connection health using ping/pong."""
        return await self.health_monitor.check_health()

    async def cleanup_connection(self) -> None:
        """Clean up WebSocket connection resources."""
        await self.lifecycle_manager.cleanup_connection()

    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self.lifecycle_manager.is_connected()

    async def send_message(self, message: str) -> bool:
        """Send message through WebSocket connection."""
        return await self.message_ops.send_message(message)

    async def receive_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """Receive message from WebSocket connection."""
        return await self.message_ops.receive_message(timeout)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed WebSocket connection information."""
        base_info = self.get_status()

        websocket_info = {
            "websocket_url": self.websocket_url,
            "is_connected": self.is_connected(),
            "ping_interval": self.health_monitor.ping_interval_seconds,
            "last_ping_time": self.health_monitor.last_ping_time,
            "last_pong_time": self.health_monitor.last_pong_time,
        }

        websocket_connection = self.lifecycle_manager.get_connection()
        if websocket_connection:
            websocket_info.update(
                {
                    "connection_closed": websocket_connection.close_code is not None,
                    "close_code": websocket_connection.close_code,
                    "local_address": getattr(websocket_connection, "local_address", None),
                    "remote_address": getattr(websocket_connection, "remote_address", None),
                }
            )

        base_info["websocket_details"] = websocket_info
        return base_info

    @property
    def websocket_connection(self) -> Any:
        """Expose underlying websocket connection for tests."""
        return self.lifecycle_manager.get_connection()

    @websocket_connection.setter
    def websocket_connection(self, connection: Any) -> None:
        self.lifecycle_manager.websocket_connection = connection
