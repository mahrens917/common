"""Recovery reporting for error analyzer."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

NOTIFICATION_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError, RuntimeError, OSError)


class RecoveryReporter:
    """Reports service recovery events."""

    def __init__(self, service_name: str, telegram_notifier: Optional[Callable] = None):
        """Initialize recovery reporter."""
        self.service_name = service_name
        self.telegram_notifier = telegram_notifier

    async def report_recovery(self, recovery_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Report service recovery.

        Args:
            recovery_message: Description of what recovered
            context: Additional context about the recovery
        """
        message = f"✅ [{self.service_name}] RECOVERY: {recovery_message}"

        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            message += f" ({context_str})"

        logger.info(message)

        # Check if recovery notification should be suppressed during routine reconnections
        from ..alert_suppression_manager import AlertType, get_alert_suppression_manager

        suppression_manager = await get_alert_suppression_manager()

        # Check if this is during a reconnection period where recovery notifications should be suppressed
        suppression_decision = await suppression_manager.should_suppress_alert(
            service_name=self.service_name,
            alert_type=AlertType.RECOVERY,
            error_message=recovery_message,
        )

        should_suppress_recovery = suppression_decision.should_suppress
        if should_suppress_recovery:
            logger.debug(f"[{self.service_name}] Recovery notification suppressed: {suppression_decision.reason}")

        if self.telegram_notifier and not should_suppress_recovery:
            await self.telegram_notifier(message)
        elif should_suppress_recovery:
            logger.debug(
                f"[{self.service_name}] Recovery notification suppressed to avoid redundancy with connection manager notifications"
            )
