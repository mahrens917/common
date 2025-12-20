"""Public API methods for Alerter."""

from typing import Any, Callable, Dict, Optional

from src.common.alerter_helpers.alert_operations import AlertOperations
from src.common.alerter_helpers.chart_operations import ChartOperations
from src.common.alerter_helpers.price_validation_operations import PriceValidationOperations
from src.common.alerting import AlertSeverity


class PublicAPI:
    """Handles public API methods for Alerter."""

    def __init__(self, component_manager):
        """Initialize with component manager."""
        self._mgr = component_manager

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        details: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
    ) -> bool:
        """Send alert."""
        return await AlertOperations.send_alert(
            self._mgr.telegram_enabled,
            self._mgr.get_telegram_component("alert_sender"),
            message,
            severity,
            alert_type,
            details,
            target_user_id,
        )

    async def send_chart_image(
        self, image_path: str, caption: str = "", target_user_id: str | None = None
    ) -> bool:
        """Send chart."""
        return await ChartOperations.send_chart_image(
            self._mgr.telegram_enabled,
            self._mgr.get_telegram_component("delivery_mgr"),
            self._mgr.authorized_user_ids,
            image_path,
            caption,
            target_user_id,
        )

    async def send_chart(
        self, image_path: str, caption: str = "", target_user_id: str | None = None
    ) -> bool:
        """Alias for send_chart_image."""
        return await self.send_chart_image(image_path, caption, target_user_id)

    def set_metrics_recorder(self, recorder) -> None:
        """Set metrics recorder."""
        self._mgr.chart_mgr.set_metrics_recorder(recorder)

    def register_command_handler(self, command: str, handler: Callable) -> None:
        """Register command handler."""
        if self._mgr.telegram_enabled:
            self._mgr.cmd_registry.register_command_handler(command, handler)

    async def poll_telegram_updates(self) -> None:
        """Poll Telegram updates."""
        if self._mgr.telegram_enabled:
            await self._mgr.polling_coord.poll_updates()

    def should_send_price_validation_alert(self, currency: str, details: Dict[str, Any]) -> bool:
        """Check if price validation alert should be sent."""
        return PriceValidationOperations.should_send_alert(
            self._mgr.telegram_enabled,
            self._mgr.get_telegram_component("price_tracker"),
            currency,
            details,
        )

    def clear_price_validation_alert(self, currency: str) -> bool:
        """Clear price validation alert."""
        return PriceValidationOperations.clear_alert(
            self._mgr.telegram_enabled, self._mgr.get_telegram_component("price_tracker"), currency
        )

    def is_price_validation_alert_active(self, currency: str) -> bool:
        """Check if price validation alert is active."""
        return PriceValidationOperations.is_alert_active(
            self._mgr.telegram_enabled, self._mgr.get_telegram_component("price_tracker"), currency
        )
