"""Health monitoring coordination logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from ..connection_state import ConnectionState


class HealthCoordinator:
    """Coordinates connection health monitoring."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        lifecycle_manager: Any,
        health_monitor: Any,
        health_check_interval: float,
        max_consecutive_failures: int,
    ):
        """Initialize health coordinator."""
        self.service_name = service_name
        self.state_manager = state_manager
        self.lifecycle_manager = lifecycle_manager
        self.health_monitor = health_monitor
        self.health_check_interval = health_check_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        self.reconnection_task: Any = None

    def _transition_state(self, new_state: ConnectionState, error_context: str | None = None) -> None:
        """Transition to a new connection state."""
        self.state_manager.transition_state(new_state, error_context)

    async def start_health_monitoring(
        self,
        check_connection_health: Callable[[], Any],
        connect_with_retry: Callable[[], Any],
    ) -> None:
        """Start background health monitoring task."""
        from .health_coordinator_helpers import HealthChecker, ReconnectionManager

        self.logger.info(f"Starting health monitoring for {self.service_name}")

        health_checker = HealthChecker(self.service_name, self.state_manager, self.logger)
        reconnection_mgr = ReconnectionManager(self.service_name, self.logger)

        while not self.lifecycle_manager.shutdown_requested:
            try:
                should_continue = await self._process_health_cycle(
                    check_connection_health,
                    connect_with_retry,
                    health_checker,
                    reconnection_mgr,
                )

                if should_continue:
                    await asyncio.sleep(self.health_check_interval)
                    self.health_monitor.reset_failures()

            except (
                ConnectionError,
                TimeoutError,
                RuntimeError,
            ) as error:  # Transient network/connection failure  # policy_guard: allow-silent-handler
                await self._handle_monitoring_error(error)

    async def _process_health_cycle(
        self,
        check_connection_health: Callable[[], Any],
        connect_with_retry: Callable[[], Any],
        health_checker,
        reconnection_mgr,
    ) -> bool:
        """
        Process one health monitoring cycle.

        Returns:
            True to continue monitoring
        """
        state = self.state_manager.get_state()

        if state == ConnectionState.READY:
            _, self.reconnection_task = await health_checker.check_and_handle_failure(
                check_connection_health,
                connect_with_retry,
                self.reconnection_task,
            )
            return True

        if state == ConnectionState.DISCONNECTED:
            _, self.reconnection_task = await reconnection_mgr.handle_disconnected(
                connect_with_retry,
                self.reconnection_task,
            )
            return True

        return True

    async def _handle_monitoring_error(self, error: Exception) -> None:
        """Handle errors during monitoring."""
        self.logger.error(f"Health monitoring error for {self.service_name}")
        self.health_monitor.increment_failures()

        if self.health_monitor.should_raise_error(self.max_consecutive_failures):
            raise error

        await asyncio.sleep(self.health_check_interval)
