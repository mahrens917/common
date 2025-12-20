"""Execute individual Telegram polling requests."""

import logging
from dataclasses import dataclass
from typing import Any, Dict

import aiohttp

logger = logging.getLogger(__name__)

# HTTP status codes
_HTTP_OK = 200
_HTTP_TOO_MANY_REQUESTS = 429


@dataclass(frozen=True)
class TelegramPollingConfig:
    """Configuration for Telegram long polling."""

    url: str
    params: Dict[str, Any]
    timeout: aiohttp.ClientTimeout
    long_poll_timeout: int


class TelegramPollingRequestExecutor:
    """Executes Telegram polling HTTP requests."""

    def __init__(
        self,
        rate_limit_handler,
        update_processor,
        backoff_manager,
        flush_pending_callback,
    ):
        """
        Initialize polling request executor.

        Args:
            rate_limit_handler: Rate limit handler
            update_processor: Update processor
            backoff_manager: Network backoff manager
            flush_pending_callback: Callback to flush pending deliveries
        """
        self.rate_limit_handler = rate_limit_handler
        self.update_processor = update_processor
        self.backoff_manager = backoff_manager
        self.flush_pending_callback = flush_pending_callback

    async def execute_polling_request(
        self,
        session: aiohttp.ClientSession,
        config: TelegramPollingConfig,
    ) -> None:
        """
        Execute a single polling request.

        Args:
            session: HTTP session
            config: Polling configuration
        """
        async with session.get(config.url, params=config.params) as response:
            if response.status == _HTTP_TOO_MANY_REQUESTS:
                await self.rate_limit_handler.handle_rate_limit(response)
                return
            if response.status != _HTTP_OK:
                logger.error(f"Failed to get Telegram updates: {response.status}")
                return

            payload = await response.json()
            if await self._handle_poll_payload(payload):
                self.backoff_manager.clear_backoff()
                await self.flush_pending_callback()

    async def _handle_poll_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Handle polling response payload.

        Args:
            payload: JSON response from Telegram

        Returns:
            True if successful
        """
        if not payload.get("ok"):
            logger.error(f"Telegram API error: {payload}")
            return False

        updates = payload.get("result")
        if not isinstance(updates, list):
            logger.debug("No new Telegram updates")
            return True
        if not updates:
            logger.debug("No new Telegram updates")
            return True

        for update in updates:
            await self.update_processor.process_update(update)
        return True
