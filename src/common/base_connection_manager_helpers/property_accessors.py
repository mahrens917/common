"""Property accessors for BaseConnectionManager.

This module provides property definitions that are mixed into BaseConnectionManager
to reduce class size.
"""

from typing import Any, Optional, Protocol


class _PropertyAccessorContext(Protocol):
    state_manager: Any
    lifecycle_manager: Any
    health_coordinator: Any
    health_check_task_handle: Optional[Any]
    reconnection_task_handle: Optional[Any]
    shutdown_requested_flag: bool


class PropertyAccessorsMixin:
    """Mixin providing property accessors for connection manager state."""

    @property
    def state_tracker(self: _PropertyAccessorContext) -> Optional[Any]:
        """Get the state tracker from state manager."""
        return getattr(self.state_manager, "state_tracker", None)

    @state_tracker.setter
    def state_tracker(self: _PropertyAccessorContext, value: Any) -> None:
        """Set the state tracker on state manager."""
        self.state_manager.state_tracker = value

    @property
    def health_check_task(self: _PropertyAccessorContext) -> Optional[Any]:
        """Get the health check task."""
        return self.health_check_task_handle

    @health_check_task.setter
    def health_check_task(self: _PropertyAccessorContext, value: Any) -> None:
        """Set the health check task."""
        self.health_check_task_handle = value
        if hasattr(self.lifecycle_manager, "health_check_task"):
            self.lifecycle_manager.health_check_task = value

    @property
    def reconnection_task(self: _PropertyAccessorContext) -> Optional[Any]:
        """Get the reconnection task."""
        coordinator_task = getattr(self.health_coordinator, "reconnection_task", None)
        return coordinator_task or self.reconnection_task_handle

    @reconnection_task.setter
    def reconnection_task(self: _PropertyAccessorContext, value: Any) -> None:
        """Set the reconnection task."""
        self.reconnection_task_handle = value
        if hasattr(self.health_coordinator, "reconnection_task"):
            self.health_coordinator.reconnection_task = value
        if hasattr(self.lifecycle_manager, "reconnection_task"):
            self.lifecycle_manager.reconnection_task = value

    @property
    def shutdown_requested(self: _PropertyAccessorContext) -> bool:
        """Get shutdown requested flag."""
        return self.shutdown_requested_flag

    @shutdown_requested.setter
    def shutdown_requested(self: _PropertyAccessorContext, value: bool) -> None:
        """Set shutdown requested flag."""
        self.shutdown_requested_flag = value
        setattr(self.lifecycle_manager, "shutdown_requested", value)
