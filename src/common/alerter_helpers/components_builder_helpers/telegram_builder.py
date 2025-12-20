"""Build Telegram-specific components."""

import asyncio
import logging

from ...alerting import TelegramClient
from ..command_authorization_checker import CommandAuthorizationChecker
from ..command_handler_registry import CommandHandlerRegistry
from ..command_queue_processor import CommandQueueProcessor
from ..telegram_delivery_manager import TelegramDeliveryManager
from ..telegram_media_sender import TelegramMediaSender
from ..telegram_message_sender import TelegramMessageSender
from ..telegram_network_backoff_manager import TelegramNetworkBackoffManager
from ..telegram_polling_coordinator import (
    TelegramCoordinatorConfig,
    TelegramCoordinatorDependencies,
    TelegramPollingCoordinator,
)
from ..telegram_polling_request_executor import TelegramPollingRequestExecutor
from ..telegram_rate_limit_handler import TelegramRateLimitHandler
from ..telegram_update_processor import TelegramUpdateProcessor

logger = logging.getLogger(__name__)


class TelegramBuilder:
    """Builds Telegram-specific helper components."""

    @staticmethod
    def build_telegram_config(settings):
        """Build Telegram configuration."""
        telegram_settings = settings.telegram
        if telegram_settings is not None:
            timeout = settings.alerting.telegram_timeout_seconds
            result = {
                "telegram_enabled": True,
                "telegram_token": telegram_settings.bot_token,
                "authorized_user_ids": list(telegram_settings.chat_ids),
                "telegram_timeout_seconds": timeout,
                "telegram_long_poll_timeout_seconds": min(60, max(25, int(timeout * 2))),
                "telegram_client": TelegramClient(
                    telegram_settings.bot_token, timeout_seconds=timeout
                ),
            }
            logger.info(
                "Telegram notifications enabled for %s authorized user(s)",
                len(result["authorized_user_ids"]),
            )
            return result
        else:
            logger.info("Telegram notifications disabled - configuration not provided")
            return {
                "telegram_enabled": False,
                "telegram_token": None,
                "authorized_user_ids": [],
                "telegram_timeout_seconds": 0,
                "telegram_long_poll_timeout_seconds": 0,
                "telegram_client": None,
            }

    @staticmethod
    def build_basic_and_command_components(result, send_alert_callback):
        """Build basic Telegram messaging and command components."""
        timeout, client, user_ids = (
            result["telegram_timeout_seconds"],
            result["telegram_client"],
            result["authorized_user_ids"],
        )
        backoff_mgr, cmd_queue = TelegramNetworkBackoffManager(timeout), asyncio.Queue()
        msg_sender, media_sender = TelegramMessageSender(
            client, timeout, backoff_mgr
        ), TelegramMediaSender(client, timeout, backoff_mgr)
        auth_checker, cmd_registry = CommandAuthorizationChecker(user_ids), CommandHandlerRegistry()
        return {
            "backoff_manager": backoff_mgr,
            "message_sender": msg_sender,
            "media_sender": media_sender,
            "delivery_manager": TelegramDeliveryManager(
                msg_sender, media_sender, result["alert_formatter"]
            ),
            "rate_limit_handler": TelegramRateLimitHandler(),
            "authorization_checker": auth_checker,
            "command_registry": cmd_registry,
            "command_queue": cmd_queue,
            "command_processor": CommandQueueProcessor(cmd_queue, send_alert_callback),
            "update_processor": TelegramUpdateProcessor(
                auth_checker, cmd_registry, cmd_queue, send_alert_callback
            ),
        }

    @staticmethod
    def build_polling_components(
        result, send_alert_callback, flush_callback, ensure_processor_callback
    ):
        """Build polling coordinator components."""
        client, timeout = result["telegram_client"], result["telegram_timeout_seconds"]
        polling_executor = TelegramPollingRequestExecutor(
            result["rate_limit_handler"],
            result["update_processor"],
            result["backoff_manager"],
            flush_callback,
        )
        config = TelegramCoordinatorConfig(
            telegram_client=client,
            telegram_timeout_seconds=timeout,
            telegram_long_poll_timeout_seconds=result["telegram_long_poll_timeout_seconds"],
        )
        dependencies = TelegramCoordinatorDependencies(
            rate_limit_handler=result["rate_limit_handler"],
            request_executor=polling_executor,
            backoff_manager=result["backoff_manager"],
            update_processor=result["update_processor"],
            queue_processor_starter=ensure_processor_callback,
        )
        return {
            "polling_executor": polling_executor,
            "polling_coordinator": TelegramPollingCoordinator(
                config=config,
                dependencies=dependencies,
            ),
        }
