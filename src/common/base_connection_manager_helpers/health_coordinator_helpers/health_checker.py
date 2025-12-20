"""Health checking utilities."""

from __future__ import annotations

import logging
from typing import Any, Callable

from ...connection_state import ConnectionState


class HealthChecker:
    """Performs health checks and transitions state on failure."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        logger: logging.Logger,
    ):
        """Initialize health checker."""
        self.service_name = service_name
        self.state_manager = state_manager
        self.logger = logger

    async def check_and_handle_failure(
        self,
        check_connection_health: Callable[[], Any],
        connect_with_retry: Callable[[], Any],
        reconnection_task: Any,
    ) -> tuple[bool, Any]:
        """
        Check health and handle failure if needed.

        Args:
            check_connection_health: Health check callback
            connect_with_retry: Reconnection callback
            reconnection_task: Current reconnection task

        Returns:
            Tuple of (should_continue, new_reconnection_task)
        """
        result = await check_connection_health()
        is_healthy = getattr(result, "healthy", bool(result))

        if is_healthy:
            return True, reconnection_task

        self.logger.warning(f"Health check failed for {self.service_name}")
        self.state_manager.transition_state(ConnectionState.DISCONNECTED, "Health check failed")

        new_task = self._ensure_reconnection_task(connect_with_retry, reconnection_task)
        return True, new_task

    def _ensure_reconnection_task(
        self,
        connect_with_retry: Callable[[], Any],
        current_task: Any,
    ) -> Any:
        """Ensure reconnection task is running."""
        import asyncio

        if not current_task or current_task.done():
            return asyncio.create_task(connect_with_retry())
        return current_task
