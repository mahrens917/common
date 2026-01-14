"""Minimal alerter for logging alerts."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from .alerter_helpers.alert_suppression_manager import AlertSuppressionManager
from .alerter_helpers.price_validation_tracker import PriceValidationTracker
from .alerting import Alert, AlerterError, AlertSeverity, AlertThrottle

ALERT_FAILURE_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError, RuntimeError)

if TYPE_CHECKING:
    from .config.shared import AlerterSettings

logger = logging.getLogger(__name__)

__all__ = [
    "ALERT_FAILURE_ERRORS",
    "Alerter",
    "Alert",
    "AlertSeverity",
    "AlerterError",
]


class Alerter:
    """Simple alerter that logs alerts."""

    def __init__(self, settings: AlerterSettings | None = None):
        from .config.shared import get_alerter_settings

        if settings is None:
            settings = get_alerter_settings()
        self.settings = settings
        self.suppression_manager = AlertSuppressionManager()
        self.price_tracker = PriceValidationTracker()
        self.alert_throttle = AlertThrottle(
            settings.alerting.throttle_window_seconds,
            settings.alerting.max_alerts_per_window,
        )

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        details: Optional[Dict[str, Any]] = None,
        _target_user_id: Optional[str] = None,
    ) -> bool:
        """Send alert (logs the message)."""
        if self.suppression_manager.should_suppress_alert(alert_type):
            return True

        alert = Alert(
            message=message,
            severity=severity,
            timestamp=time.time(),
            alert_type=alert_type,
            details=details,
        )

        if not self.alert_throttle.record(alert):
            logger.debug("Alert throttled: %s", alert_type)
            return False

        logger.info("Alert: [%s] %s", severity.value, message)
        return True

    async def send_chart_image(self, _image_path: str, _caption: str = "", _target_user_id: str | None = None) -> bool:
        """Chart sending is not supported without telegram."""
        return False

    async def send_chart(self, _image_path: str, _caption: str = "", _target_user_id: str | None = None) -> bool:
        """Chart sending is not supported without telegram."""
        return False

    def should_send_price_validation_alert(self, currency: str, details: Dict[str, Any]) -> bool:
        """Check if price validation alert should be sent."""
        return self.price_tracker.should_send_alert(currency, details)

    def clear_price_validation_alert(self, currency: str) -> bool:
        """Clear price validation alert for currency."""
        return self.price_tracker.clear_alert(currency)

    def is_price_validation_alert_active(self, currency: str) -> bool:
        """Check if price validation alert is active."""
        return self.price_tracker.is_alert_active(currency)

    async def cleanup(self) -> None:
        """No cleanup needed without telegram."""
        pass
