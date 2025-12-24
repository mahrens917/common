"""Coordinates Alerter initialization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from common.alerter_helpers.alert_sender import AlertSender, AlertSenderConfig
from common.alerter_helpers.alerter_components_builder import AlerterComponentsBuilder

if TYPE_CHECKING:
    from src.monitor.settings import MonitorSettings


class InitializationCoordinator:
    """Coordinates Alerter initialization and component setup."""

    @staticmethod
    def initialize_components(
        settings: MonitorSettings,
        send_alert_callback: Callable,
        flush_callback: Callable,
        ensure_proc_callback: Callable,
    ) -> Dict[str, Any]:
        """
        Initialize all alerter components.

        Args:
            settings: Monitor settings
            send_alert_callback: Callback for sending alerts
            flush_callback: Callback for flushing
            ensure_proc_callback: Callback for ensuring processor

        Returns:
            Dictionary containing all initialized components
        """
        components = AlerterComponentsBuilder(settings).build(send_alert_callback, flush_callback, ensure_proc_callback)

        result = {
            "telegram_enabled": components["telegram_enabled"],
            "authorized_user_ids": components["authorized_user_ids"],
        }

        if components["telegram_enabled"]:
            result.update(
                {
                    "delivery_manager": components["delivery_manager"],
                    "command_registry": components["command_registry"],
                    "command_processor": components["command_processor"],
                    "polling_coordinator": components["polling_coordinator"],
                    "price_validation_tracker": components["price_validation_tracker"],
                    "alert_sender": InitializationCoordinator._create_alert_sender(components, send_alert_callback, ensure_proc_callback),
                }
            )

        return result

    @staticmethod
    def _create_alert_sender(
        components: Dict[str, Any],
        send_alert_callback: Callable,
        ensure_proc_callback: Callable,
    ) -> AlertSender:
        """Create and configure AlertSender."""
        sender_config = AlertSenderConfig(
            suppression_manager=components["suppression_manager"],
            alert_throttle=components["alert_throttle"],
            telegram_enabled=True,
            authorized_user_ids=components["authorized_user_ids"],
            delivery_manager=components["delivery_manager"],
            ensure_processor_callback=ensure_proc_callback,
        )
        return AlertSender(sender_config)
