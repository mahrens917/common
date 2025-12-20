"""Process individual Telegram updates from polling."""

import asyncio
import logging
import time
from typing import Any, Dict

from ..alerting import QueuedCommand
from .unauthorized_command_handler import UnauthorizedCommandHandler

logger = logging.getLogger(__name__)

DEFAULT_TELEGRAM_MESSAGE_TEXT = ""


class TelegramUpdateProcessor:
    """Processes individual Telegram updates (messages/commands)."""

    def __init__(
        self,
        authorization_checker,
        handler_registry,
        command_queue: asyncio.Queue,
        send_alert_callback,
    ):
        """
        Initialize update processor.

        Args:
            authorization_checker: Authorization checker
            handler_registry: Command handler registry
            command_queue: Queue for authorized commands
            send_alert_callback: Callback to send alerts
        """
        self.authorization_checker = authorization_checker
        self.handler_registry = handler_registry
        self.command_queue = command_queue
        self.send_alert_callback = send_alert_callback
        self.unauthorized_handler = UnauthorizedCommandHandler(send_alert_callback)
        self.last_update_id = 0

    async def process_update(self, update: Dict[str, Any]) -> None:
        """
        Process a single Telegram update.

        Args:
            update: Telegram update object
        """
        if "update_id" in update:
            self.last_update_id = update["update_id"]

        message = update.get("message")
        if not isinstance(message, dict):
            return

        text = message.get("text")
        if not isinstance(text, str):
            text = DEFAULT_TELEGRAM_MESSAGE_TEXT
        if not text.startswith("/"):
            return

        command = text[1:].split()[0]
        if not self.authorization_checker.is_authorized_user(message):
            await self.unauthorized_handler.handle_unauthorized_attempt(command, message)
            return

        if self.handler_registry.has_handler(command):
            await self._queue_authorized_command(command, message)

    async def _queue_authorized_command(self, command: str, message: Dict[str, Any]) -> None:
        """Queue authorized command for processing."""
        original_handler = self.handler_registry.get_handler(command)
        if original_handler is None:
            return

        queued_command = QueuedCommand(
            command=command,
            handler=original_handler,
            message=message,
            timestamp=time.time(),
        )

        await self.command_queue.put(queued_command)
        logger.debug("Queued command /%s for processing", command)
