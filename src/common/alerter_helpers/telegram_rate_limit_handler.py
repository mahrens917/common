"""Telegram API rate limiting (429) handling."""

import logging
import time
from typing import Optional

import aiohttp

from .telegram_retry_after_parser import TelegramRetryAfterParser

logger = logging.getLogger(__name__)


class TelegramRateLimitHandler:
    """Handles Telegram API rate limiting (429 responses) with backoff."""

    def __init__(self, max_429_retries: int = 3):
        """
        Initialize rate limit handler.

        Args:
            max_429_retries: Maximum number of 429 retries before giving up
        """
        self._last_429_time: Optional[float] = None
        self._429_count: int = 0
        self._max_429_retries = max_429_retries
        self._last_429_backoff_seconds: Optional[float] = None
        self._retry_parser = TelegramRetryAfterParser()

    def is_backoff_active(self) -> bool:
        """
        Check if currently in backoff period.

        Returns:
            True if backoff is active
        """
        if self._last_429_time is None:
            return False

        backoff_time = self._last_429_backoff_seconds
        if backoff_time is None:
            backoff_time = min(300, 30 * (2**self._429_count))

        time_since_429 = time.time() - self._last_429_time
        if time_since_429 < backoff_time:
            logger.debug(
                "Telegram API backoff active, %.1fs remaining",
                backoff_time - time_since_429,
            )
            return True

        logger.info(
            "Telegram API backoff period ended after %.1fs (waited %.1fs)",
            time_since_429,
            backoff_time,
        )
        self._last_429_time = None
        self._429_count = 0
        self._last_429_backoff_seconds = None
        return False

    async def handle_rate_limit(self, response: aiohttp.ClientResponse) -> None:
        """
        Handle 429 rate limit response.

        Args:
            response: HTTP response with 429 status
        """
        retry_after_seconds = await self._retry_parser.extract_retry_after_seconds(response)
        self._last_429_time = time.time()
        if retry_after_seconds is not None:
            backoff_time = retry_after_seconds
            self._last_429_backoff_seconds = backoff_time
            self._429_count = 0
            logger.warning(
                "Telegram API rate limited (429); retrying after %ss per server guidance",
                backoff_time,
            )
        else:
            self._429_count = min(self._429_count + 1, self._max_429_retries)
            backoff_time = min(300, 30 * (2**self._429_count))
            self._last_429_backoff_seconds = backoff_time
            logger.warning(
                "Telegram API rate limited (429), implementing %ss backoff (attempt %s)",
                backoff_time,
                self._429_count,
            )
