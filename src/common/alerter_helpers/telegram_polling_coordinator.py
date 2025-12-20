"""Coordinates Telegram polling with backoff and error handling."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import aiohttp

from ..alerting import TelegramClient
from .telegram_network_backoff_manager import TelegramNetworkBackoffManager
from .telegram_polling_request_executor import (
    TelegramPollingConfig,
    TelegramPollingRequestExecutor,
)
from .telegram_rate_limit_handler import TelegramRateLimitHandler
from .telegram_update_processor import TelegramUpdateProcessor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramCoordinatorConfig:
    """Configuration for Telegram polling coordinator."""

    telegram_client: Optional[TelegramClient]
    telegram_timeout_seconds: int
    telegram_long_poll_timeout_seconds: int


@dataclass(frozen=True)
class TelegramCoordinatorDependencies:
    """Dependencies for Telegram polling coordinator."""

    rate_limit_handler: TelegramRateLimitHandler
    request_executor: TelegramPollingRequestExecutor
    backoff_manager: TelegramNetworkBackoffManager
    update_processor: TelegramUpdateProcessor
    queue_processor_starter: Callable[[], None]


class TelegramPollingCoordinator:
    """Coordinates Telegram polling lifecycle with rate limiting."""

    def __init__(
        self,
        config: TelegramCoordinatorConfig,
        dependencies: TelegramCoordinatorDependencies,
    ):
        """
        Initialize polling coordinator.

        Args:
            config: Telegram polling configuration
            dependencies: Polling dependencies
        """
        self.telegram_client: Optional[TelegramClient] = config.telegram_client
        self.telegram_timeout_seconds = config.telegram_timeout_seconds
        self.telegram_long_poll_timeout_seconds = config.telegram_long_poll_timeout_seconds
        self.rate_limit_handler: TelegramRateLimitHandler = dependencies.rate_limit_handler
        self.request_executor: TelegramPollingRequestExecutor = dependencies.request_executor
        self.backoff_manager: TelegramNetworkBackoffManager = dependencies.backoff_manager
        self.update_processor: TelegramUpdateProcessor = dependencies.update_processor
        self.queue_processor_starter: Callable[[], None] = dependencies.queue_processor_starter

    async def poll_updates(self) -> None:
        """Poll Telegram for command updates."""
        if not self._can_poll():
            return

        if self.rate_limit_handler.is_backoff_active():
            return

        try:
            config = self._create_polling_config()
        except RuntimeError:
            return

        try:
            async with aiohttp.ClientSession(timeout=config.timeout) as session:
                await self.request_executor.execute_polling_request(session, config)
        except asyncio.TimeoutError:
            logger.debug("Telegram long polling timeout (expected)")
        except (
            aiohttp.ClientError,
            OSError,
        ) as exc:
            logger.exception("Error polling Telegram updates")
            self.backoff_manager.record_failure(exc)

    def _can_poll(self) -> bool:
        """Check if polling is possible."""
        self.queue_processor_starter()
        if self.backoff_manager.should_skip_operation("getUpdates"):
            return False
        return True

    def _create_polling_config(self) -> TelegramPollingConfig:
        """Create polling configuration."""
        long_poll_timeout = self.telegram_long_poll_timeout_seconds
        if not long_poll_timeout:
            long_poll_timeout = max(25, self.telegram_timeout_seconds * 2)
        long_poll_timeout = max(5, int(long_poll_timeout))

        if self.telegram_client is None:
            logger.debug("Telegram client not configured; skipping update poll")
            raise RuntimeError("telegram client unavailable")

        timeout = aiohttp.ClientTimeout(total=long_poll_timeout + 5)
        params = {
            "offset": self.update_processor.last_update_id + 1,
            "timeout": long_poll_timeout,
        }
        url = f"{self.telegram_client.base_url}/getUpdates"
        return TelegramPollingConfig(
            url=url, params=params, timeout=timeout, long_poll_timeout=long_poll_timeout
        )
