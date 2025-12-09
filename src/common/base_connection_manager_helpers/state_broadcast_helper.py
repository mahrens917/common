"""State broadcast helpers for connection manager."""

from typing import Any, Optional

from ..connection_state import ConnectionState


async def broadcast_state_change(
    manager: Any, new_state: ConnectionState, error_context: Optional[str] = None
) -> None:
    """Helper used by tests that patch broadcast behavior directly."""
    if manager.state_tracker is None:
        await manager._initialize_state_tracker()
    await manager._state_manager_broadcast(new_state, error_context)


async def initialize_state_tracker(manager: Any) -> None:
    """Delegate tracker initialization to the state manager."""
    await manager._state_tracker_initializer()
