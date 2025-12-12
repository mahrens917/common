"""Batch timer management."""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

BATCH_PROCESS_ERRORS = (
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
    LookupError,
    RedisError,
)


class BatchTimer:
    """Manages batch timing and triggers."""

    def __init__(
        self,
        batch_time_seconds: float,
        on_timeout: Callable[[], Awaitable[None]],
        name: str,
    ):
        """
        Initialize batch timer.

        Args:
            batch_time_seconds: Time threshold in seconds
            on_timeout: Callback when timer expires
            name: Name for logging
        """
        self.batch_time_seconds = batch_time_seconds
        self.on_timeout = on_timeout
        self.name = name
        self._task: Optional[asyncio.Task] = None

    def start(self, batch_size: int) -> None:
        """
        Start timer.

        Args:
            batch_size: Current batch size for logging
        """
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._run(batch_size))

    async def _run(self, batch_size: int) -> None:
        """Run timer and call timeout callback."""
        try:
            logger.debug(f"{self.name}: Timer started - " f"Waiting {self.batch_time_seconds}s with {batch_size} items in batch")
            await asyncio.sleep(self.batch_time_seconds)

            logger.debug(f"{self.name}: Timer expired - Triggering timeout callback")
            await self.on_timeout()

        except asyncio.CancelledError:  # policy_guard: allow-silent-handler
            pass  # Timer cancelled, probably during shutdown
        except BATCH_PROCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.exception(
                "Error in batch timer for %s (%s): %s",
                self.name,
                type(exc).__name__,
            )

    def cancel(self) -> None:
        """Cancel timer if running."""
        if self._task and not self._task.done():
            self._task.cancel()

    async def wait_for_cancellation(self) -> None:
        """Wait for timer cancellation to complete."""
        if self._task and not self._task.done():
            try:
                await self._task
            except asyncio.CancelledError:  # policy_guard: allow-silent-handler
                pass

    def is_running(self) -> bool:
        """Check if timer is running."""
        return self._task is not None and not self._task.done()
