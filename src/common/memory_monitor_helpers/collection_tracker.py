"""Collection tracking for memory monitoring."""

import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)

COLLECTION_ERRORS = (RuntimeError, ValueError, KeyError, AttributeError, TypeError)


class CollectionTracker:
    """Tracks collection sizes for memory leak detection."""

    def __init__(self):
        """Initialize collection tracker."""
        self.tracked_collections: Dict[str, Callable[[], int]] = {}

    def track_collection(self, name: str, size_getter: Callable[[], int]) -> None:
        """
        Track a collection's size for memory leak detection.

        Args:
            name: Name of the collection (e.g., 'response_queues', 'background_tasks')
            size_getter: Function that returns the current size of the collection
        """
        self.tracked_collections[name] = size_getter
        logger.debug(f"Now tracking collection '{name}' for memory leaks")

    def get_collection_sizes(self) -> Dict[str, int]:
        """
        Get sizes of all tracked collections.

        Returns:
            Dictionary mapping collection names to sizes
        """
        collection_sizes = {}
        for name, size_getter in self.tracked_collections.items():
            try:
                collection_sizes[name] = size_getter()
            except COLLECTION_ERRORS as e:  # policy_guard: allow-silent-handler
                logger.warning(f"Failed to get size for collection '{name}': {e}")
                collection_sizes[name] = -1
        return collection_sizes

    def get_tracked_collection_names(self) -> list:
        """Get list of tracked collection names."""
        return list(self.tracked_collections.keys())
