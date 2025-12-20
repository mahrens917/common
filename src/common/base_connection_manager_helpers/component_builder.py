"""Component builder for connection manager initialization."""

from __future__ import annotations

from typing import Any


def _build_core_components(service_name: str) -> dict[str, Any]:
    from .metrics_tracker import MetricsTracker
    from .state_manager import ConnectionStateManager

    state_manager = ConnectionStateManager(service_name)
    metrics_tracker = MetricsTracker()
    return {"state_manager": state_manager, "metrics_tracker": metrics_tracker}


def _build_handlers(service_name: str, config: Any, state_manager: Any, metrics_tracker: Any) -> dict[str, Any]:
    from .connection_lifecycle import ConnectionLifecycleManager
    from .health_monitor import ConnectionHealthMonitor
    from .notification_handler import NotificationHandler
    from .reconnection_handler import ReconnectionHandler
    from .state_transition import StateTransitionHandler

    reconnection_handler = ReconnectionHandler(
        service_name,
        config.reconnection_initial_delay_seconds,
        config.reconnection_max_delay_seconds,
        config.reconnection_backoff_multiplier,
        config.max_consecutive_failures,
        metrics_tracker,
    )
    notification_handler = NotificationHandler(service_name, state_manager, metrics_tracker)
    lifecycle_manager = ConnectionLifecycleManager(service_name)
    health_monitor = ConnectionHealthMonitor(service_name)
    state_transition_handler = StateTransitionHandler(state_manager, metrics_tracker)
    return {
        "reconnection_handler": reconnection_handler,
        "notification_handler": notification_handler,
        "lifecycle_manager": lifecycle_manager,
        "health_monitor": health_monitor,
        "state_transition_handler": state_transition_handler,
    }


def _build_coordinators(
    service_name: str,
    config: Any,
    state_manager: Any,
    metrics_tracker: Any,
    handlers: dict[str, Any],
) -> dict[str, Any]:
    from .health_coordinator import HealthCoordinator
    from .retry_coordinator import RetryCoordinator
    from .startup_coordinator import StartupCoordinator
    from .status_reporter import StatusReporter

    retry_coordinator = RetryCoordinator(
        service_name,
        state_manager,
        metrics_tracker,
        handlers["reconnection_handler"],
        handlers["lifecycle_manager"],
        handlers["notification_handler"],
        config.max_consecutive_failures,
    )
    health_coordinator = HealthCoordinator(
        service_name,
        state_manager,
        handlers["lifecycle_manager"],
        handlers["health_monitor"],
        config.health_check_interval_seconds,
        config.max_consecutive_failures,
    )
    startup_coordinator = StartupCoordinator(service_name, state_manager, handlers["lifecycle_manager"])
    status_reporter = StatusReporter(service_name, state_manager, metrics_tracker, config)
    return {
        "retry_coordinator": retry_coordinator,
        "health_coordinator": health_coordinator,
        "startup_coordinator": startup_coordinator,
        "status_reporter": status_reporter,
    }


class ComponentBuilder:
    """Builds and configures all connection manager components."""

    def __init__(self, service_name: str, config: Any):
        self.service_name = service_name
        self.config = config

    def build_all(self) -> dict[str, Any]:
        core = _build_core_components(self.service_name)
        handlers = _build_handlers(self.service_name, self.config, core["state_manager"], core["metrics_tracker"])
        coordinators = _build_coordinators(
            self.service_name,
            self.config,
            core["state_manager"],
            core["metrics_tracker"],
            handlers,
        )
        return {**core, **handlers, **coordinators}
