"""Connection manager startup coordination logic."""

import asyncio
import logging
from typing import Any, Callable


class StartupCoordinator:
    """Coordinates connection manager startup and shutdown."""

    def __init__(
        self,
        service_name: str,
        state_manager: Any,
        lifecycle_manager: Any,
    ):
        """Initialize startup coordinator."""
        self.service_name = service_name
        self.state_manager = state_manager
        self.lifecycle_manager = lifecycle_manager
        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        self.health_check_task: Any = None

    async def start(
        self,
        connect_with_retry: Callable[[], Any],
        start_health_monitoring: Callable[[], Any],
    ) -> bool:
        """Start the connection manager."""
        self.logger.info(f"Starting connection manager for {self.service_name}")
        await self.state_manager._initialize_state_tracker()
        connection_successful = await connect_with_retry()

        if connection_successful:
            self.health_check_task = asyncio.create_task(start_health_monitoring())
            self.logger.info(f"Connection manager started for {self.service_name}")
            return True
        else:
            self.logger.error(f"Failed to start connection manager for {self.service_name}")
            return False

    async def stop(self, cleanup_connection: Callable[[], Any]) -> None:
        """Stop the connection manager and clean up resources."""
        await self.lifecycle_manager.stop(cleanup_connection)
