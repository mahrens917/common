"""Helper for sending alerts with throttling and suppression."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from ..alerting import Alert, AlertSeverity, AlertThrottle

logger = logging.getLogger(__name__)


@dataclass
class AlertSenderConfig:
    """Configuration for AlertSender."""

    suppression_manager: Any
    alert_throttle: AlertThrottle
    telegram_enabled: bool
    authorized_user_ids: List[str]
    delivery_manager: Any
    ensure_processor_callback: Callable


class AlertDeliveryMixin:
    # Declare dynamically-attached attributes for static type checking
    alert_throttle: AlertThrottle
    suppression_manager: Any
    ensure_processor_callback: Callable
    delivery_manager: Any
    authorized_user_ids: List[str]

    def _should_send_alert(self, alert: Alert, alert_type: str) -> bool:
        assert self.alert_throttle is not None
        if self.suppression_manager.should_suppress_alert(alert_type):
            return False
        if not self.alert_throttle.record(alert):
            logger.debug(f"Alert throttled: {alert_type}")
            return False
        return True

    def _is_suppressed(self, alert_type: str) -> bool:
        return self.suppression_manager.should_suppress_alert(alert_type)

    async def _send_telegram_alert(self, alert: Alert, target_user_id: Optional[str]) -> bool:
        assert self.ensure_processor_callback is not None
        self.ensure_processor_callback()
        assert self.delivery_manager is not None
        authorized_user_ids = self.authorized_user_ids
        assert authorized_user_ids is not None
        recipients = self._collect_recipients(target_user_id, authorized_user_ids)
        if not recipients:
            return False
        return await self._deliver_telegram(alert, recipients)

    def _collect_recipients(
        self, target_user_id: Optional[str], authorized_user_ids: List[str]
    ) -> List[str]:
        recipients = [target_user_id] if target_user_id else list(authorized_user_ids)
        if not recipients:
            logger.warning("Telegram alert dropped; no authorized recipients configured")
        return recipients

    async def _deliver_telegram(self, alert: Alert, recipients: List[str]) -> bool:
        try:
            result = await self.delivery_manager.send_alert(alert, recipients)
            if hasattr(result, "success") and not getattr(result, "success"):
                logger.warning("Telegram alert delivery skipped or failed (backoff active?)")
                return False
        except asyncio.CancelledError:
            logger.info("Telegram alert send cancelled during shutdown")
            return False
        except (RuntimeError, ValueError, TypeError) as exc:
            return self._handle_telegram_exception(exc)
        else:
            return True

    def _handle_telegram_exception(self, exc: Exception) -> bool:
        if getattr(self.suppression_manager, "is_shutdown_in_progress", None) and (
            self.suppression_manager.is_shutdown_in_progress()
        ):
            logger.info("Telegram alert failed during shutdown; ignoring error: %s", exc)
            return False

        logger.exception("Failed to send Telegram alert")
        return False


class AlertSender(AlertDeliveryMixin):
    """Handles alert sending with throttling, suppression, and delivery."""

    # Override mixin declarations to allow Optional during initialization
    alert_throttle: Optional[AlertThrottle]
    authorized_user_ids: Optional[List[str]]
    ensure_processor_callback: Optional[Callable]

    def __init__(
        self,
        config_or_suppression_manager,
        alert_throttle: Optional[AlertThrottle] = None,
        telegram_enabled: Optional[bool] = None,
        authorized_user_ids: Optional[List[str]] = None,
        delivery_manager=None,
        ensure_processor_callback=None,
    ):
        """Initialize with dependencies or config object."""
        if isinstance(config_or_suppression_manager, AlertSenderConfig):
            config = config_or_suppression_manager
            self.suppression_manager = config.suppression_manager
            self.alert_throttle = config.alert_throttle
            self.telegram_enabled = config.telegram_enabled
            self.authorized_user_ids = config.authorized_user_ids
            self.delivery_manager = config.delivery_manager
            self.ensure_processor_callback = config.ensure_processor_callback
        else:
            self.suppression_manager = config_or_suppression_manager
            self.alert_throttle = alert_throttle
            self.telegram_enabled = telegram_enabled
            self.authorized_user_ids = authorized_user_ids
            self.delivery_manager = delivery_manager
            self.ensure_processor_callback = ensure_processor_callback

        if self.alert_throttle is None:
            raise ValueError("AlertSender requires an AlertThrottle instance")

        if self.telegram_enabled:
            if self.authorized_user_ids is None:
                raise ValueError("Authorized user IDs are required when Telegram is enabled")
            if self.delivery_manager is None:
                raise ValueError("Delivery manager is required when Telegram is enabled")
            if self.ensure_processor_callback is None:
                raise ValueError("Processor callback is required when Telegram is enabled")

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        alert_type: str = "general",
        details: Optional[Dict[str, Any]] = None,
        target_user_id: Optional[str] = None,
    ) -> bool:
        alert = Alert(
            message=message,
            severity=severity,
            timestamp=time.time(),
            alert_type=alert_type,
            details=details,
        )

        if not self._should_send_alert(alert, alert_type):
            return self._is_suppressed(alert_type)

        if self.telegram_enabled:
            return await self._send_telegram_alert(alert, target_user_id)

        logger.info(f"Alert (no channels enabled): [{severity.value}] {message}")
        return True
