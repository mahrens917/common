"""Batch execution logic with error handling."""

import logging
from typing import Awaitable, Callable, Generic, List, TypeVar

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

T = TypeVar("T")


class BatchExecutor(Generic[T]):
    """Handles batch execution with error handling."""

    def __init__(self, process_batch: Callable[[List[T]], Awaitable[None]], name: str):
        """
        Initialize batch executor.

        Args:
            process_batch: Async function to process a batch
            name: Name for logging
        """
        self.process_batch = process_batch
        self.name = name

    async def execute(self, batch: List[T], batch_size: int, batch_time: float, reason: str) -> None:
        """
        Execute batch processing.

        Args:
            batch: Items to process
            batch_size: Size of batch
            batch_time: Time batch was collecting
            reason: Reason for processing
        """
        if not batch:
            return

        logger.info(f"{self.name}: Processing batch of {batch_size} items " f"after {batch_time*1000:.1f}ms ({reason})")

        logger.debug(f"{self.name}: Processing batch contents:\n" + "\n".join(f"- {item}" for item in batch))

        try:
            await self.process_batch(batch)
            logger.debug(f"{self.name}: Batch processing complete")
        except BATCH_PROCESS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.exception(
                "Error processing batch in %s (%s)",
                self.name,
                type(exc).__name__,
            )
            raise
