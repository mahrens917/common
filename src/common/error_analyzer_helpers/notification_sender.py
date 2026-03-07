"""Telegram notification for error analysis."""

import asyncio
import logging
from typing import Callable, Optional

from common.truthy import pick_if

from .analysis import ErrorAnalysis, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)

NOTIFICATION_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError, RuntimeError, OSError)


class NotificationSender:
    """Sends Telegram notifications for errors."""

    def __init__(self, service_name: str, telegram_notifier: Optional[Callable] = None):
        """Initialize notification sender."""
        self.service_name = service_name
        self.telegram_notifier = telegram_notifier

    async def send_telegram_notification(self, analysis: ErrorAnalysis) -> None:
        """Send Telegram notification for error."""
        if not self.telegram_notifier:
            return

        # Create severity emoji
        severity_emoji = {
            ErrorSeverity.LOW: "⚠️",
            ErrorSeverity.MEDIUM: "🔶",
            ErrorSeverity.HIGH: "🔴",
            ErrorSeverity.CRITICAL: "🚨",
        }

        # Create category emoji
        category_emoji = {
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.WEBSOCKET: "🔌",
            ErrorCategory.AUTHENTICATION: "🔐",
            ErrorCategory.API: "📡",
            ErrorCategory.DATA: "📊",
            ErrorCategory.DEPENDENCY: "🔗",
            ErrorCategory.CONFIGURATION: "⚙️",
            ErrorCategory.RESOURCE: "💾",
            ErrorCategory.UNKNOWN: "❓",
        }

        emoji = severity_emoji.get(analysis.severity)
        if emoji is None:
            raise ValueError(f"Unknown error severity: {analysis.severity}")
        cat_emoji = category_emoji.get(analysis.category)
        if cat_emoji is None:
            raise ValueError(f"Unknown error category: {analysis.category}")

        message = f"{emoji} [{analysis.service_name}] ERROR DETECTED\n\n"
        message += f"{cat_emoji} Category: {analysis.category.value.title()}\n"
        message += f"📋 Severity: {analysis.severity.value.title()}\n"
        message += f"💥 Error: {analysis.error_message}\n"
        message += f"🔍 Root Cause: {analysis.root_cause}\n"
        message += f"🛠️ Suggested Action: {analysis.suggested_action}\n"

        if analysis.context:
            context_str = ", ".join([f"{k}={v}" for k, v in analysis.context.items()])
            message += f"📝 Context: {context_str}\n"

        recovery_emoji = pick_if(analysis.recovery_possible, lambda: "✅", lambda: "❌")
        recovery_status = pick_if(analysis.recovery_possible, lambda: "Possible", lambda: "Manual intervention required")
        message += f"{recovery_emoji} Auto-recovery: {recovery_status}"

        try:
            await self.telegram_notifier(message)
        except NOTIFICATION_ERRORS:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.exception(f"[{self.service_name}] Failed to send error notification: ")
