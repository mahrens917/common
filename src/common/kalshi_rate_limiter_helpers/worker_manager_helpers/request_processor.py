"""Request processing utilities."""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RequestProcessor:
    """Processes queued requests with token management."""

    def __init__(self, token_manager: Any, executor: Any):
        """Initialize request processor."""
        self.token_manager = token_manager
        self.executor = executor

    async def process_read_request(self, read_queue: asyncio.Queue) -> bool:
        """
        Process a read request if tokens available.

        Args:
            read_queue: Queue containing read requests

        Returns:
            True if request was processed
        """
        if not self.token_manager.has_read_tokens():
            return False

        if read_queue.empty():
            return False

        try:
            request_data = read_queue.get_nowait()
            self.token_manager.consume_read_token()
            await self.executor.execute_request(request_data)

            logger.debug(
                f"[KalshiRateLimiter] Processed READ request "
                f"{request_data['request_id']}, tokens remaining: {self.token_manager.read_tokens}"
            )

        except asyncio.QueueEmpty:  # policy_guard: allow-silent-handler
            return False
        else:
            return True

    async def process_write_request(self, write_queue: asyncio.Queue) -> bool:
        """
        Process a write request if tokens available.

        Args:
            write_queue: Queue containing write requests

        Returns:
            True if request was processed
        """
        if not self.token_manager.has_write_tokens():
            return False

        if write_queue.empty():
            return False

        try:
            request_data = write_queue.get_nowait()
            self.token_manager.consume_write_token()
            await self.executor.execute_request(request_data)

            logger.debug(
                f"[KalshiRateLimiter] Processed WRITE request "
                f"{request_data['request_id']}, tokens remaining: {self.token_manager.write_tokens}"
            )

        except asyncio.QueueEmpty:  # policy_guard: allow-silent-handler
            return False
        else:
            return True
