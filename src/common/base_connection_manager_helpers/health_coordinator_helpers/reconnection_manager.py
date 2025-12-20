"""Reconnection management utilities."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable


class ReconnectionManager:
    """Manages reconnection tasks for disconnected services."""

    def __init__(
        self,
        service_name: str,
        logger: logging.Logger,
    ):
        """Initialize reconnection manager."""
        self.service_name = service_name
        self.logger = logger

    async def handle_disconnected(
        self,
        connect_with_retry: Callable[[], Any],
        reconnection_task: Any,
    ) -> tuple[bool, Any]:
        """
        Handle disconnected state and trigger reconnection.

        Args:
            connect_with_retry: Reconnection callback
            reconnection_task: Current reconnection task

        Returns:
            Tuple of (should_continue, new_reconnection_task)
        """
        self.logger.info(f"Service {self.service_name} is disconnected, triggering reconnection")

        new_task = self._start_reconnection_if_needed(connect_with_retry, reconnection_task)
        return True, new_task

    def _start_reconnection_if_needed(
        self,
        connect_with_retry: Callable[[], Any],
        current_task: Any,
    ) -> Any:
        """Start reconnection task if not already running."""
        if not current_task or current_task.done():
            self.logger.info(f"Starting reconnection task for {self.service_name}")
            return asyncio.create_task(connect_with_retry())
        return current_task
