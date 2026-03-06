"""Collection size tracking with error isolation per collector."""

from __future__ import annotations

import contextlib
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class CollectionTracker:
    """Tracks named collections and retrieves their sizes via registered getters."""

    def __init__(self) -> None:
        self._collections: dict[str, Callable[[], int]] = {}

    def track_collection(self, name: str, getter: Callable[[], int]) -> None:
        """Register a collection size getter under the given name."""
        self._collections[name] = getter

    def get_collection_sizes(self) -> dict[str, int]:
        """Return a dict mapping each collection name to its current size.

        Returns -1 for any collection whose getter raises an exception.
        """
        sizes: dict[str, int] = {}
        for name, getter in self._collections.items():
            size = -1
            with contextlib.suppress(ValueError, TypeError, RuntimeError, KeyError, AttributeError, OSError):
                size = getter()
            sizes[name] = size
            if size == -1:
                logger.warning("Failed to get size for collection '%s'", name)
        return sizes


__all__ = ["CollectionTracker"]
