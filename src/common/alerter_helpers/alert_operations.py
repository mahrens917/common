"""Alert operations for Alerter."""

import logging
from typing import Any, Dict, Optional

from common.alerting import AlertSeverity

logger = logging.getLogger(__name__)


class AlertOperations:
    """Handles alert sending operations."""

    @staticmethod
    async def send_alert(
        telegram_enabled: bool,
        alert_sender,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        details: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
    ) -> bool:
        """
        Send alert message.

        Args:
            telegram_enabled: Whether Telegram is enabled
            alert_sender: Alert sender instance
            message: Alert message
            severity: Alert severity level
            alert_type: Type of alert
            details: Optional alert details
            target_user_id: Optional target user ID

        Returns:
            True if successful, False otherwise
        """
        if telegram_enabled:
            return await alert_sender.send_alert(message, severity, alert_type, details, target_user_id)
        logger.info(f"Alert (no channels): [{severity.value}] {message}")
        return True
