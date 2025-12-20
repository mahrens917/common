"""Initialization helper for Alerter."""

import asyncio
import logging
from typing import Any, Dict

from ..alerting import AlertThrottle, TelegramClient
from .alert_formatter import AlertFormatter
from .alert_suppression_manager import AlertSuppressionManager
from .command_authorization_checker import CommandAuthorizationChecker
from .command_handler_registry import CommandHandlerRegistry
from .price_validation_tracker import PriceValidationTracker
from .telegram_delivery_manager import TelegramDeliveryManager
from .telegram_media_sender import TelegramMediaSender
from .telegram_message_sender import TelegramMessageSender
from .telegram_network_backoff_manager import TelegramNetworkBackoffManager
from .telegram_rate_limit_handler import TelegramRateLimitHandler

logger = logging.getLogger(__name__)


class AlerterInitializer:
    """Handles initialization of Alerter components."""

    def __init__(self, settings):
        """Initialize with monitor settings."""
        self.settings = settings

    def initialize(self) -> Dict[str, Any]:
        """Initialize all alerter components and return them as a dict."""
        result = {}

        # Initialize Telegram configuration
        telegram_settings = self.settings.telegram
        if telegram_settings is not None:
            result["telegram_enabled"] = True
            result["telegram_token"] = telegram_settings.bot_token
            result["authorized_user_ids"] = list(telegram_settings.chat_ids)
            result["telegram_timeout_seconds"] = self.settings.alerting.telegram_timeout_seconds
            result["telegram_long_poll_timeout_seconds"] = min(
                60, max(25, int(result["telegram_timeout_seconds"] * 2))
            )
            result["telegram_client"] = TelegramClient(
                result["telegram_token"], timeout_seconds=result["telegram_timeout_seconds"]
            )
            logger.info(
                "Telegram notifications enabled for %s authorized user(s)",
                len(result["authorized_user_ids"]),
            )
        else:
            result["telegram_enabled"] = False
            result["telegram_token"] = None
            result["authorized_user_ids"] = []
            result["telegram_timeout_seconds"] = 0
            result["telegram_long_poll_timeout_seconds"] = 0
            result["telegram_client"] = None
            logger.info("Telegram notifications disabled - configuration not provided")

        # Initialize core helpers
        result["alert_formatter"] = AlertFormatter()
        result["suppression_manager"] = AlertSuppressionManager()
        result["price_validation_tracker"] = PriceValidationTracker()

        # Throttling configuration
        throttle_window = self.settings.alerting.throttle_window_seconds
        max_alerts = self.settings.alerting.max_alerts_per_window
        result["alert_throttle"] = AlertThrottle(throttle_window, max_alerts)

        # Initialize Telegram helpers if enabled
        if result["telegram_enabled"]:
            self._initialize_telegram_helpers(result)

        return result

    def _initialize_telegram_helpers(self, result: Dict[str, Any]) -> None:
        """Initialize Telegram-specific helpers."""
        result["backoff_manager"] = TelegramNetworkBackoffManager(
            result["telegram_timeout_seconds"]
        )
        result["message_sender"] = TelegramMessageSender(
            result["telegram_client"],
            result["telegram_timeout_seconds"],
            result["backoff_manager"],
        )
        result["media_sender"] = TelegramMediaSender(
            result["telegram_client"],
            result["telegram_timeout_seconds"],
            result["backoff_manager"],
        )
        result["delivery_manager"] = TelegramDeliveryManager(
            result["message_sender"], result["media_sender"], result["alert_formatter"]
        )
        result["rate_limit_handler"] = TelegramRateLimitHandler()
        result["authorization_checker"] = CommandAuthorizationChecker(result["authorized_user_ids"])
        result["command_registry"] = CommandHandlerRegistry()

        # Command queue setup
        result["command_queue"] = asyncio.Queue()

        # Note: send_alert callback will be provided by Alerter after initialization
        result["command_processor"] = None  # Will be set by Alerter
        result["update_processor"] = None  # Will be set by Alerter
        result["polling_executor"] = None  # Will be set by Alerter
        result["polling_coordinator"] = None  # Will be set by Alerter
