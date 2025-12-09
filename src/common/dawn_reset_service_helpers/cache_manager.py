"""Cache management for dawn reset checks."""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DAWN_CACHE_MAX_SIZE = 10


class CacheManager:
    """
    Manages cache for dawn check results to avoid redundant calculations.

    Caches dawn check results keyed by coordinates and timestamps to
    improve performance and reduce logging verbosity.
    """

    def __init__(self):
        """Initialize the cache manager."""
        self._dawn_check_cache: Dict[Tuple[str, str, str], Tuple[bool, Optional[datetime]]] = {}
        self._max_cache_size = DEFAULT_DAWN_CACHE_MAX_SIZE

    def get_cache_key(
        self,
        latitude: float,
        longitude: float,
        previous_timestamp: datetime,
        current_timestamp: datetime,
    ) -> Tuple[str, str, str]:
        """
        Generate cache key for dawn check.

        Args:
            latitude: Weather station latitude
            longitude: Weather station longitude
            previous_timestamp: Previous timestamp
            current_timestamp: Current timestamp

        Returns:
            Tuple cache key
        """
        return (
            f"{latitude:.4f},{longitude:.4f}",
            previous_timestamp.replace(second=0, microsecond=0).isoformat(),
            current_timestamp.replace(second=0, microsecond=0).isoformat(),
        )

    def get_cached_result(
        self, cache_key: Tuple[str, str, str]
    ) -> Optional[Tuple[bool, Optional[datetime]]]:
        """
        Get cached dawn check result if available.

        Args:
            cache_key: Cache key from get_cache_key

        Returns:
            Cached result or None if not in cache
        """
        return self._dawn_check_cache.get(cache_key)

    def cache_result(
        self, cache_key: Tuple[str, str, str], result: Tuple[bool, Optional[datetime]]
    ) -> None:
        """
        Cache a dawn check result.

        Args:
            cache_key: Cache key from get_cache_key
            result: Result to cache
        """
        self._dawn_check_cache[cache_key] = result

        # Clean old cache entries (keep only last max_cache_size to prevent memory growth)
        if len(self._dawn_check_cache) > self._max_cache_size:
            # Remove oldest entries
            oldest_keys = list(self._dawn_check_cache.keys())[: -self._max_cache_size]
            for old_key in oldest_keys:
                del self._dawn_check_cache[old_key]

    def is_cache_empty(self) -> bool:
        """Check if cache is empty."""
        return len(self._dawn_check_cache) == 0
