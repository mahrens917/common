"""Telegram network backoff management."""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNetworkBackoffManager:
    """Manages network backoff when Telegram API becomes unreachable."""

    def __init__(self, telegram_timeout_seconds: int):
        """
        Initialize backoff manager.

        Args:
            telegram_timeout_seconds: Timeout for Telegram operations
        """
        self.telegram_timeout_seconds = telegram_timeout_seconds
        self._block_until: Optional[float] = None
        self._reason: Optional[str] = None
        self._logged = False

    def should_skip_operation(self, action: str) -> bool:
        """
        Check if operation should be skipped due to backoff.

        Args:
            action: Name of action being attempted

        Returns:
            True if operation should be skipped
        """
        if self._block_until is None:
            return False

        remaining = self._block_until - time.time()
        if remaining > 0:
            if not self._logged:
                logger.warning(
                    "Telegram %s skipped; network still unreachable for %.1fs (%s)",
                    action,
                    max(0.0, remaining),
                    self._reason if self._reason else "unknown error",
                )
                self._logged = True
            return True

        self.clear_backoff()
        return False

    def record_failure(self, exception: Exception) -> None:
        """
        Record network failure and enter backoff period.

        Args:
            exception: Exception that caused the failure
        """
        cooldown = max(60, self.telegram_timeout_seconds * 2)
        self._block_until = time.time() + cooldown
        message_text = str(exception)
        if message_text:
            self._reason = message_text
        else:
            self._reason = exception.__class__.__name__
        self._logged = False
        logger.warning(
            "Telegram API unreachable, backing off for %.0fs (%s)",
            cooldown,
            self._reason,
        )

    def clear_backoff(self) -> None:
        """Clear backoff state after successful operation."""
        if self._block_until is None:
            return

        self._block_until = None
        self._reason = None
        self._logged = False
