"""Batch collection and state management."""

import logging
import time
from typing import Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BatchCollector(Generic[T]):
    """Manages batch collection and state tracking."""

    def __init__(self, batch_size: int, name: str):
        """
        Initialize batch collector.

        Args:
            batch_size: Maximum number of items per batch
            name: Name for logging
        """
        self.batch_size = batch_size
        self.name = name
        self.current_batch: List[T] = []
        self.batch_start_time: Optional[float] = None

    def add_item(self, item: T) -> bool:
        """
        Add item to batch.

        Args:
            item: Item to add

        Returns:
            True if batch size threshold reached, False otherwise
        """
        # Start timing if this is first item
        if not self.current_batch:
            self.batch_start_time = time.time()

        logger.debug(
            f"{self.name}: Adding item to batch:\n"
            f"- Current batch size: {len(self.current_batch)}\n"
            f"- Item: {item}"
        )

        self.current_batch.append(item)

        # Check if size threshold reached
        if len(self.current_batch) >= self.batch_size:
            logger.debug(
                f"{self.name}: Size threshold reached ({self.batch_size}), processing batch"
            )
            return True

        return False

    def get_batch(self) -> List[T]:
        """
        Get current batch and reset state.

        Returns:
            Current batch items
        """
        batch = self.current_batch
        self.current_batch = []
        self.batch_start_time = None
        return batch

    def get_batch_metrics(self) -> tuple[int, float]:
        """
        Get current batch metrics.

        Returns:
            Tuple of (batch_size, batch_time_seconds)
        """
        batch_size = len(self.current_batch)
        batch_time = time.time() - (self.batch_start_time or time.time())
        return batch_size, batch_time

    def has_items(self) -> bool:
        """Check if batch has items."""
        return len(self.current_batch) > 0

    def clear(self) -> None:
        """Clear batch state."""
        self.current_batch = []
        self.batch_start_time = None
