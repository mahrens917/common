"""Proxy setup for connection manager components."""

from typing import Any, Optional

from ..connection_state import ConnectionState


def setup_component_proxies(manager: Any) -> None:
    """Configure proxies between components and manager methods."""
    _setup_state_broadcast_proxy(manager)
    _setup_notification_proxy(manager)
    _setup_backoff_calculator_proxy(manager)


def _setup_state_broadcast_proxy(manager: Any) -> None:
    """Proxy state broadcasts through manager's broadcast method."""
    original_broadcast = manager.state_manager._broadcast_state_change

    def _state_broadcast_proxy(new_state: ConnectionState, error_context: Optional[str] = None):
        return manager._broadcast_state_change(new_state, error_context)

    manager.state_manager._broadcast_state_change = _state_broadcast_proxy
    manager._state_manager_broadcast = original_broadcast


def _setup_notification_proxy(manager: Any) -> None:
    """Proxy notifications through manager's notification method."""

    async def _notify(is_connected: bool, details: str = "") -> None:
        await manager.send_connection_notification(is_connected, details)

    manager.retry_coordinator._send_notification = _notify


def _setup_backoff_calculator_proxy(manager: Any) -> None:
    """Proxy backoff calculations through manager's calculate method."""
    manager.reconnection_handler.calculate_backoff_delay = lambda: manager.calculate_backoff_delay()
