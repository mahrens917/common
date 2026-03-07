"""Health monitoring coordination logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from ..connection_state import ConnectionState


class ConnectionHealthMonitor:
    """Monitors connection health."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_monitor_failures = 0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def reset_failures(self) -> None:
        """Reset failure counter."""
        self.health_monitor_failures = 0

    def increment_failures(self) -> None:
        """Increment failure counter."""
        self.health_monitor_failures += 1

    def get_failure_count(self) -> int:
        """Get failure count."""
        return self.health_monitor_failures

    def should_raise_error(self, max_failures: int) -> bool:
        """Check if should raise error due to too many failures."""
        return self.health_monitor_failures >= max_failures


class HealthChecker:
    """Performs health checks and transitions state on failure."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        logger: logging.Logger,
    ):
        self.service_name = service_name
        self.state_manager = state_manager
        self.logger = logger

    async def check_and_handle_failure(
        self,
        check_connection_health: Callable[[], Any],
        connect_with_retry: Callable[[], Any],
        reconnection_task: Any,
    ) -> tuple[bool, Any]:
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
        if not current_task or current_task.done():
            return asyncio.create_task(connect_with_retry())
        return current_task


class ReconnectionManager:
    """Manages reconnection tasks for disconnected services."""

    def __init__(self, service_name: str, logger: logging.Logger):
        self.service_name = service_name
        self.logger = logger

    async def handle_disconnected(
        self,
        connect_with_retry: Callable[[], Any],
        reconnection_task: Any,
    ) -> tuple[bool, Any]:
        self.logger.info(f"Service {self.service_name} is disconnected, triggering reconnection")
        new_task = self._start_reconnection_if_needed(connect_with_retry, reconnection_task)
        return True, new_task

    def _start_reconnection_if_needed(
        self,
        connect_with_retry: Callable[[], Any],
        current_task: Any,
    ) -> Any:
        if not current_task or current_task.done():
            self.logger.info(f"Starting reconnection task for {self.service_name}")
            return asyncio.create_task(connect_with_retry())
        return current_task


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
