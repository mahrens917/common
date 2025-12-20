"""Component manager for Alerter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from src.common.alerter_helpers.chart_manager import ChartManager
from src.common.alerter_helpers.command_coordinator import CommandCoordinator
from src.common.alerter_helpers.command_registration import CommandRegistration
from src.common.alerter_helpers.initialization_coordinator import InitializationCoordinator

if TYPE_CHECKING:
    from src.monitor.settings import MonitorSettings


class ComponentManager:
    """Manages Alerter components and initialization."""

    def __init__(
        self,
        settings: MonitorSettings,
        send_alert_callback: Callable,
        flush_callback: Callable,
        ensure_proc_callback: Callable,
        send_chart_callback: Callable,
    ):
        """Initialize component manager."""
        self.components = InitializationCoordinator.initialize_components(
            settings, send_alert_callback, flush_callback, ensure_proc_callback
        )

        self.telegram_enabled = self.components["telegram_enabled"]
        self.authorized_user_ids = self.components["authorized_user_ids"]

        # Initialize telegram-specific components
        if self.telegram_enabled:
            self.delivery_mgr = self.components["delivery_manager"]
            self.cmd_registry = self.components["command_registry"]
            self.cmd_processor = self.components["command_processor"]
            self.polling_coord = self.components["polling_coordinator"]
            self.price_tracker = self.components["price_validation_tracker"]
            self.alert_sender = self.components["alert_sender"]

        # Initialize chart and command coordination
        self.chart_mgr = ChartManager(self.telegram_enabled)
        self.cmd_coord = CommandCoordinator(
            self.chart_mgr, send_alert_callback, send_chart_callback
        )

        # Register commands if telegram is enabled
        if self.telegram_enabled:
            CommandRegistration.register_commands(self.cmd_registry, self.cmd_coord)

    def get_telegram_component(self, name: str) -> Any:
        """Get telegram component by name, or None if telegram disabled."""
        if not self.telegram_enabled:
            return None
        return getattr(self, name, None)
