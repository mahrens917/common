"""Monitoring loop helper for dependency monitor."""

import asyncio
import logging
import time
from typing import Dict

from .dependency_checker import DependencyState, DependencyStatus

logger = logging.getLogger(__name__)


class MonitoringLoop:
    """Handles the main dependency monitoring loop."""

    def __init__(
        self,
        service_name: str,
        dependencies: Dict[str, DependencyState],
        dependency_checker,
        status_manager,
    ):
        """
        Initialize monitoring loop.

        Args:
            service_name: Name of service
            dependencies: Dictionary of dependency states
            dependency_checker: Dependency checker instance
            status_manager: Status manager instance
        """
        self.service_name = service_name
        self.dependencies = dependencies
        self.dependency_checker = dependency_checker
        self.status_manager = status_manager
        self.running = False

    async def run_loop(self) -> None:
        """Main monitoring loop."""
        logger.info(f"[{self.service_name}] Starting dependency monitoring loop")

        while self.running:
            try:
                for state in self.dependencies.values():
                    if not self.running:
                        break

                    current_time = time.time()
                    if current_time - state.last_check_time >= state.current_check_interval:
                        await self._check_dependency_with_notification(state)

                if self.status_manager:
                    await self.status_manager.handle_status_changes()

                await asyncio.sleep(5.0)

            except asyncio.CancelledError:  # Expected during task cancellation  # policy_guard: allow-silent-handler
                logger.debug("Expected during task cancellation")
                break

        logger.info(f"[{self.service_name}] Dependency monitoring loop ended")

    async def _check_dependency_with_notification(self, state: DependencyState) -> DependencyStatus:
        """Check dependency and notify status changes."""
        notifier = None
        if self.status_manager:
            notifier = self.status_manager.notify_status_change

        return await self.dependency_checker.check_dependency(state, notifier)

    def start(self) -> None:
        """Start the monitoring loop."""
        self.running = True

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self.running = False
