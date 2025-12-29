"""
Unified connection manager base class with Telegram notifications.

This module provides a base class for managing connections across all services
with consistent reconnection logic, health monitoring, and Telegram notifications.
"""

import asyncio as _asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol

from .base_connection_manager_helpers import (
    ComponentBuilder,
    PropertyAccessorsMixin,
    broadcast_state_change,
    calculate_backoff_delay,
    connect_with_retry,
    initialize_state_tracker,
    send_connection_notification,
    setup_component_proxies,
    start_connection_manager,
    stop_connection_manager,
)
from .connection_config import get_connection_config
from .connection_state import ConnectionState
from .health.types import HealthCheckResult

asyncio = _asyncio


class _ConnectionLifecycleContext(Protocol):
    health_check_task_handle: Optional[Any]
    reconnection_task_handle: Optional[Any]
    shutdown_requested_flag: bool
    health_coordinator: Any
    status_reporter: Any
    state_manager: Any

    async def establish_connection(self) -> bool: ...

    async def check_connection_health(self) -> HealthCheckResult: ...

    async def send_connection_notification(self, is_connected: bool, details: str = "") -> None: ...

    async def connect_with_retry(self) -> bool: ...

    def transition_state(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None: ...


class ConnectionLifecycleMixin:
    """Lifecycle helpers shared by multiple connection manager subclasses."""

    @property
    def _health_check_task(self: _ConnectionLifecycleContext):
        return self.health_check_task_handle

    @_health_check_task.setter
    def _health_check_task(self: _ConnectionLifecycleContext, value: Optional[Any]):
        self.health_check_task_handle = value

    @property
    def _reconnection_task(self: _ConnectionLifecycleContext):
        return self.reconnection_task_handle

    @_reconnection_task.setter
    def _reconnection_task(self: _ConnectionLifecycleContext, value: Optional[Any]):
        self.reconnection_task_handle = value

    @property
    def _shutdown_requested(self: _ConnectionLifecycleContext):
        return self.shutdown_requested_flag

    @_shutdown_requested.setter
    def _shutdown_requested(self: _ConnectionLifecycleContext, value: bool):
        self.shutdown_requested_flag = value

    async def send_connection_notification(self: _ConnectionLifecycleContext, is_connected: bool, details: str = "") -> None:
        """Update centralized state tracker with notification."""
        await send_connection_notification(self, is_connected, details)

    async def connect_with_retry(self: _ConnectionLifecycleContext) -> bool:
        """Attempt connection with exponential backoff retry logic."""
        return await connect_with_retry(
            self,
            self.establish_connection,
            self.send_connection_notification,
            self.transition_state,
        )

    async def start_health_monitoring(self: _ConnectionLifecycleContext) -> None:
        """Start background health monitoring task."""
        await self.health_coordinator.start_health_monitoring(self.check_connection_health, self.connect_with_retry)

    async def start(self: _ConnectionLifecycleContext) -> bool:
        """Start the connection manager."""
        return await start_connection_manager(self)

    async def stop(self: _ConnectionLifecycleContext) -> None:
        """Stop the connection manager and clean up resources."""
        await stop_connection_manager(self)

    def get_status(self: _ConnectionLifecycleContext) -> Dict[str, Any]:
        """Get current connection status and metrics."""
        return self.status_reporter.get_status()

    async def _broadcast_state_change(
        self: _ConnectionLifecycleContext,
        new_state: ConnectionState,
        error_context: Optional[str] = None,
    ) -> None:
        """Broadcast state change to listeners."""
        await broadcast_state_change(self, new_state, error_context)

    async def _initialize_state_tracker(self: _ConnectionLifecycleContext) -> None:
        """Delegate tracker initialization to the state manager."""
        await initialize_state_tracker(self)

    def calculate_backoff_delay(self: _ConnectionLifecycleContext) -> float:
        """Calculate exponential backoff delay with jitter."""
        return calculate_backoff_delay(self)

    @property
    def state(self: _ConnectionLifecycleContext) -> ConnectionState:
        """Expose the authoritative state held by the state manager."""
        return self.state_manager.state

    @state.setter
    def state(self: _ConnectionLifecycleContext, value: ConnectionState) -> None:
        """Set the connection state via the state manager."""
        self.state_manager.state = value


class BaseConnectionManager(ConnectionLifecycleMixin, PropertyAccessorsMixin, ABC):
    """Base class for managing connections with Telegram notifications."""

    def __init__(self, service_name: str, alerter: Optional[Any] = None):
        """Initialize connection manager with service-specific configuration."""
        self.service_name = service_name
        self.config = get_connection_config(service_name)
        if alerter is None:
            try:
                from common.alerter import Alerter

                self.alerter = Alerter()
            except ImportError:  # Optional module not available  # policy_guard: allow-silent-handler
                # common.alerter is optional - use null object pattern if unavailable
                self.alerter = None
        else:
            self.alerter = alerter

        # Build all components
        builder = ComponentBuilder(service_name, self.config)
        components = builder.build_all()

        # Assign components to instance
        self.state_manager = components["state_manager"]
        self.metrics_tracker = components["metrics_tracker"]
        self.reconnection_handler = components["reconnection_handler"]
        self.notification_handler = components["notification_handler"]
        self.lifecycle_manager = components["lifecycle_manager"]
        self.health_monitor = components["health_monitor"]
        self.state_transition_handler = components["state_transition_handler"]
        self.retry_coordinator = components["retry_coordinator"]
        self.health_coordinator = components["health_coordinator"]
        self.startup_coordinator = components["startup_coordinator"]
        self.status_reporter = components["status_reporter"]

        # Configure proxies between components
        setup_component_proxies(self)

        self.metrics = self.metrics_tracker.get_metrics()

        self.health_check_task_handle = None
        self.reconnection_task_handle = None
        self.shutdown_requested_flag = False
        self._state_tracker_initializer = self.state_manager._initialize_state_tracker

        self.logger = logging.getLogger(f"{__name__}.{service_name}")
        self.logger.info(f"Initialized connection manager for {service_name}")

    @abstractmethod
    async def establish_connection(self) -> bool:
        """Establish the actual connection for the service."""
        pass

    @abstractmethod
    async def check_connection_health(self) -> HealthCheckResult:
        """Check if the connection is healthy and operational."""
        pass

    @abstractmethod
    async def cleanup_connection(self) -> None:
        """Clean up connection resources."""
        pass

    def transition_state(self, new_state: ConnectionState, error_context: Optional[str] = None) -> None:
        """Transition to a new connection state."""
        self.state_transition_handler.transition_state(new_state, error_context)
        self.metrics = self.metrics_tracker.get_metrics()
