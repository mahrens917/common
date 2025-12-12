"""Request enqueueing logic for KalshiRateLimiter."""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RequestEnqueuer:
    """Handles request enqueueing logic."""

    @staticmethod
    async def enqueue_request(
        request_type,
        request_data: Dict[str, Any],
        read_queue: asyncio.Queue,
        write_queue: asyncio.Queue,
        read_queue_max_size: int,
        write_queue_max_size: int,
    ) -> str:
        """
        Queue a request for rate-limited execution.

        Args:
            request_type: RequestType.READ or RequestType.WRITE
            request_data: Request parameters including method, path, params, and callbacks
            read_queue: Read request queue
            write_queue: Write request queue
            read_queue_max_size: Maximum size of read queue
            write_queue_max_size: Maximum size of write queue

        Returns:
            request_id: Unique identifier for tracking this request

        Raises:
            QueueFullError: If request queue is at capacity
            ValueError: If request_type is invalid
        """
        from ..kalshi_rate_limiter import QueueFullError, RequestType

        request_id = str(uuid.uuid4())
        request_data["request_id"] = request_id
        request_data["enqueue_time"] = time.time()

        try:
            if request_type == RequestType.READ:
                if read_queue.full():
                    raise QueueFullError(f"Read request queue is full ({read_queue_max_size} requests) - system overloaded")
                read_queue.put_nowait(request_data)

            elif request_type == RequestType.WRITE:
                if write_queue.full():
                    raise QueueFullError(f"Write request queue is full ({write_queue_max_size} requests) - system overloaded")
                write_queue.put_nowait(request_data)

            else:
                raise ValueError(f"Invalid request type: {request_type}")

        except asyncio.QueueFull:  # policy_guard: allow-silent-handler
            # This should not happen due to full() checks above, but fail-fast if it does
            raise QueueFullError(f"Request queue unexpectedly full for {request_type.value}")

        logger.debug(f"[KalshiRateLimiter] Queued {request_type.value} request {request_id}")
        return request_id
