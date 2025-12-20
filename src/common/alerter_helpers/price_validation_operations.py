"""Price validation operations for Alerter."""

from typing import Any, Dict


class PriceValidationOperations:
    """Handles price validation alert operations."""

    @staticmethod
    def should_send_alert(
        telegram_enabled: bool, price_tracker, currency: str, details: Dict[str, Any]
    ) -> bool:
        """Check if price validation alert should be sent."""
        return price_tracker.should_send_alert(currency, details) if telegram_enabled else False

    @staticmethod
    def clear_alert(telegram_enabled: bool, price_tracker, currency: str) -> bool:
        """Clear price validation alert for currency."""
        return price_tracker.clear_alert(currency) if telegram_enabled else False

    @staticmethod
    def is_alert_active(telegram_enabled: bool, price_tracker, currency: str) -> bool:
        """Check if price validation alert is active."""
        return price_tracker.is_alert_active(currency) if telegram_enabled else False
