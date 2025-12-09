"""Lifecycle helpers for connection manager."""

import asyncio
import contextlib
from typing import Any

from ..connection_state import ConnectionState


async def start_connection_manager(manager: Any) -> bool:
    """Start the connection manager."""
    await manager._initialize_state_tracker()
    connection_successful = await manager.connect_with_retry()
    if not connection_successful:
        return False
    manager.health_check_task = asyncio.create_task(manager.start_health_monitoring())
    return True


async def stop_connection_manager(manager: Any) -> None:
    """Stop the connection manager and clean up resources."""
    manager.shutdown_requested = True
    tasks = [manager.health_check_task, manager.reconnection_task]
    for task in tasks:
        if task and hasattr(task, "cancel"):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
    await manager.cleanup_connection()
    manager.transition_state(ConnectionState.DISCONNECTED)
    manager.logger.info(f"Connection manager stopped for {manager.service_name}")
