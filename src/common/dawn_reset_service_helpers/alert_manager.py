"""Telegram alert management for dawn reset service."""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

ALERT_DELIVERY_ERRORS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    OSError,
)


class AlertManager:
    """
    Manages Telegram alerts for dawn reset events.

    Tracks reset status to avoid duplicate alerts and sends notifications
    for important reset events.
    """

    def __init__(self, telegram_handler=None):
        """
        Initialize alert manager.

        Args:
            telegram_handler: Optional telegram handler for sending alerts
        """
        self.telegram_handler = telegram_handler
        self._last_reset_status: Dict[str, bool] = {}

    async def send_reset_alert(self, station_id: str, field_name: str, was_reset: bool, previous_value: Any, new_value: Any) -> None:
        """
        Send Telegram alert about reset status.

        Args:
            station_id: Weather station ID
            field_name: Field being reset
            was_reset: Whether reset occurred
            previous_value: Previous value before reset
            new_value: New value after reset
        """
        if not self.telegram_handler:
            return

        # Track reset status to avoid duplicate alerts
        status_key = f"{station_id}:{field_name}"
        last_status = self._last_reset_status.get(status_key)

        # Only send alert if status changed or it's a critical reset
        if last_status == was_reset and not (was_reset and field_name == "max_temp_f"):
            return

        self._last_reset_status[status_key] = was_reset

        try:
            if was_reset:
                if field_name == "max_temp_f":
                    message = (
                        f"✅ DAWN RESET SUCCESS: {station_id}\n"
                        f"Field: {field_name}\n"
                        f"Previous: {previous_value}°F\n"
                        f"Reset to: {new_value}°F\n"
                        f"Trading day started fresh"
                    )
                else:
                    message = f"✅ DAWN RESET: {station_id} - {field_name} cleared for new trading day"
            else:
                # Don't send notifications when dawn is skipped
                return

            await self.telegram_handler.send_custom_message(message)

        except ALERT_DELIVERY_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.exception(f"Failed to send dawn reset telegram alert: ")
