"""Price validation alert tempering to prevent flooding."""

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PriceValidationTracker:
    """
    Tracks active price validation alerts to prevent flooding.

    Implements alert tempering:
    - Send first alert immediately when validation fails
    - Suppress subsequent alerts for same currency until condition resolves
    - Track per currency (BTC and ETH independently)
    """

    def __init__(self):
        """Initialize price validation alert tracker."""
        self.active_price_alerts: Dict[str, Dict[str, Any]] = {}

    def should_send_alert(self, currency: str, alert_details: Dict[str, Any]) -> bool:
        """
        Check if price validation alert should be sent.

        Args:
            currency: Currency identifier ('BTC' or 'ETH')
            alert_details: Alert details including prices and difference

        Returns:
            True if alert should be sent, False if suppressed
        """
        alert_key = f"cfb_price_validation_{currency}"

        # If no active alert for this currency, send it
        if alert_key not in self.active_price_alerts:
            self.active_price_alerts[alert_key] = {
                "first_alert_time": time.time(),
                "details": alert_details,
                "currency": currency,
            }
            logger.info(f"CFB price validation alert activated for {currency}")
            return True

        # Alert already active for this currency, suppress
        logger.debug(f"CFB price validation alert suppressed for {currency} (already active)")
        return False

    def clear_alert(self, currency: str) -> bool:
        """
        Clear active price validation alert when condition resolves.

        Args:
            currency: Currency identifier ('BTC' or 'ETH')

        Returns:
            True if alert was cleared (was active), False if no active alert
        """
        alert_key = f"cfb_price_validation_{currency}"

        if alert_key in self.active_price_alerts:
            del self.active_price_alerts[alert_key]
            logger.info(f"CFB price validation alert cleared for {currency}")
            return True

        return False

    def is_alert_active(self, currency: str) -> bool:
        """
        Check if price validation alert is currently active.

        Args:
            currency: Currency identifier ('BTC' or 'ETH')

        Returns:
            True if alert is active, False otherwise
        """
        alert_key = f"cfb_price_validation_{currency}"
        return alert_key in self.active_price_alerts
