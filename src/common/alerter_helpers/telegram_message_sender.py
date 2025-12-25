"""Telegram message sending functionality."""

import asyncio
import logging
from typing import List

import aiohttp

from ..alerting import TelegramClient, TelegramDeliveryResult

logger = logging.getLogger(__name__)


class TelegramMessageSender:
    """Sends text messages to Telegram recipients."""

    def __init__(
        self,
        telegram_client: TelegramClient,
        timeout_seconds: int,
        backoff_manager,
    ):
        """
        Initialize message sender.

        Args:
            telegram_client: Telegram API client
            timeout_seconds: Timeout for send operations
            backoff_manager: Network backoff manager
        """
        self.telegram_client = telegram_client
        self.timeout_seconds = timeout_seconds
        self.backoff_manager = backoff_manager

    async def send_message(
        self,
        formatted_message: str,
        recipients: List[str],
    ) -> TelegramDeliveryResult:
        """
        Send text message to Telegram recipients.

        Args:
            formatted_message: Formatted message to send
            recipients: List of Telegram chat IDs

        Returns:
            TelegramDeliveryResult

        Raises:
            RuntimeError: If delivery fails
        """
        if not recipients:
            raise ValueError("Telegram message requires at least one recipient.")

        if self.backoff_manager.should_skip_operation("sendMessage"):
            logger.warning("Skipping Telegram sendMessage due to active network backoff")
            return TelegramDeliveryResult(success=False, failed_recipients=list(recipients), queued_recipients=[])

        success_count = 0
        for chat_id in recipients:
            try:
                success, error_text = await self.telegram_client.send_message(chat_id, formatted_message)
            except asyncio.TimeoutError as exc:
                self.backoff_manager.record_failure(exc)
                raise RuntimeError(f"Telegram send_message timeout after {self.timeout_seconds}s for {chat_id}") from exc
            except (aiohttp.ClientError, OSError, RuntimeError) as exc:
                self.backoff_manager.record_failure(exc)
                raise RuntimeError(f"Telegram send_message failed for {chat_id}") from exc

            if not success:
                if error_text:
                    failure_message = error_text
                else:
                    failure_message = "unknown error"
                self.backoff_manager.record_failure(RuntimeError(failure_message))
                raise RuntimeError(f"Telegram send_message returned failure for {chat_id}: {failure_message}")

            success_count += 1
            self.backoff_manager.clear_backoff()
            logger.debug("Telegram message sent to %s", chat_id)

        if success_count == 0:
            raise RuntimeError("Telegram message delivery reported zero successes unexpectedly.")

        return TelegramDeliveryResult(success=True, failed_recipients=[], queued_recipients=[])
