"""REST connection manager for unified REST API service management. Provides REST-specific connection management with HTTP health checks, session management, and request/response handling."""

import logging
from typing import Any, Callable, Dict, Optional

import aiohttp

from .connection_manager import BaseConnectionManager
from .health.types import HealthCheckResult
from .http_utils import AioHTTPSessionConnectionMixin
from .rest_connection_manager_helpers import (
    RESTConnectionLifecycle,
    RESTHealthMonitor,
    RESTRequestOperations,
    RESTSessionManager,
)
from .session_tracker import track_existing_session, track_session_close


class RESTConnectionManager(AioHTTPSessionConnectionMixin, BaseConnectionManager):
    """REST-specific connection manager."""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        health_check_endpoint: str = "/health",
        authentication_handler: Optional[Callable] = None,
        alerter: Optional[Any] = None,
    ):
        """Initialize REST connection manager."""
        super().__init__(service_name, alerter)
        self.base_url = base_url.rstrip("/")
        self.health_check_endpoint = health_check_endpoint
        self.authentication_handler = authentication_handler
        self.session_manager = RESTSessionManager(
            service_name,
            self.config.connection_timeout_seconds,
            self.config.request_timeout_seconds,
            track_existing_session,
            track_session_close,
        )
        self.health_monitor = RESTHealthMonitor(
            service_name,
            self.base_url,
            health_check_endpoint,
            self.session_manager,
            authentication_handler,
        )
        self.lifecycle_manager = RESTConnectionLifecycle(
            service_name, self.base_url, self.session_manager, self.health_monitor
        )
        self.request_ops = RESTRequestOperations(
            service_name,
            self.base_url,
            self.session_manager,
            authentication_handler,
            self.health_monitor,
        )
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    @property
    def session(self):
        """Get the current session."""
        return self.session_manager.get_session()

    @property
    def consecutive_request_failures(self) -> int:
        """Get the consecutive request failures count."""
        return self.health_monitor.consecutive_failures

    def is_connected(self) -> bool:
        """Check if the connection is active."""
        return self.session_manager.get_session() is not None

    async def establish_connection(self) -> bool:
        return await self.lifecycle_manager.establish_connection()

    async def check_connection_health(self) -> HealthCheckResult:
        return await self.health_monitor.check_health()

    async def cleanup_connection(self) -> None:
        await self.lifecycle_manager.cleanup_connection()

    async def make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[aiohttp.ClientResponse]:
        return await self.request_ops.make_request(method, endpoint, **kwargs)

    async def make_json_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        return await self.request_ops.make_json_request(method, endpoint, **kwargs)

    def get_connection_info(self) -> Dict[str, Any]:
        base_info = self.get_status()
        rest_info = {
            "base_url": self.base_url,
            "health_check_endpoint": self.health_check_endpoint,
            "is_connected": self.session_manager.get_session() is not None,
            "last_successful_request_time": self.health_monitor.last_success_time,
            "consecutive_request_failures": self.health_monitor.consecutive_failures,
        }
        session = self.session_manager.get_session()
        if session:
            connector = getattr(session, "connector", None)
            connector_info = {}
            if connector:
                connector_info = {
                    "connection_limit": getattr(connector, "limit", None),
                    "connection_limit_per_host": getattr(connector, "limit_per_host", None),
                    "closed": getattr(connector, "closed", None),
                }
            rest_info.update({"session_closed": session.closed, "connector_info": connector_info})
        base_info["rest_details"] = rest_info
        return base_info
