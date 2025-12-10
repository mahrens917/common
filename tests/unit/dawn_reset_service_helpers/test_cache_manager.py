"""Tests for dawn reset service cache manager."""

from datetime import datetime

from common.dawn_reset_service_helpers.cache_manager import CacheManager

DEFAULT_TEST_CACHE_MAX_SIZE = 3


class TestCacheManagerGetCacheKey:
    """Tests for CacheManager.get_cache_key."""

    def test_get_cache_key_formats_correctly(self) -> None:
        """Cache key should format coordinates and timestamps correctly."""
        manager = CacheManager()
        prev_ts = datetime(2024, 12, 1, 10, 30, 45, 123456)
        curr_ts = datetime(2024, 12, 1, 11, 45, 30, 654321)

        key = manager.get_cache_key(40.7128, -74.0060, prev_ts, curr_ts)

        assert key[0] == "40.7128,-74.0060"
        assert key[1] == "2024-12-01T10:30:00"
        assert key[2] == "2024-12-01T11:45:00"

    def test_get_cache_key_truncates_seconds(self) -> None:
        """Cache key should truncate seconds and microseconds."""
        manager = CacheManager()
        prev_ts = datetime(2024, 12, 1, 10, 30, 59, 999999)
        curr_ts = datetime(2024, 12, 1, 10, 31, 1, 1)

        key = manager.get_cache_key(0.0, 0.0, prev_ts, curr_ts)

        # Seconds should be zeroed out
        assert key[1].endswith(":00")
        assert key[2].endswith(":00")


class TestCacheManagerCaching:
    """Tests for CacheManager caching operations."""

    def test_get_cached_result_returns_none_for_missing(self) -> None:
        """Should return None for non-existent cache key."""
        manager = CacheManager()

        result = manager.get_cached_result(("key1", "key2", "key3"))

        assert result is None

    def test_cache_result_and_retrieve(self) -> None:
        """Should store and retrieve cache results."""
        manager = CacheManager()
        cache_key = ("40.7128,-74.0060", "2024-12-01T10:30:00", "2024-12-01T11:45:00")
        cached_value = (True, datetime(2024, 12, 1, 6, 30))

        manager.cache_result(cache_key, cached_value)
        result = manager.get_cached_result(cache_key)

        assert result == cached_value

    def test_cache_evicts_old_entries(self) -> None:
        """Should evict old entries when cache exceeds max size."""
        manager = CacheManager()
        manager._max_cache_size = DEFAULT_TEST_CACHE_MAX_SIZE

        for i in range(5):
            key = (f"loc{i}", f"prev{i}", f"curr{i}")
            manager.cache_result(key, (True, None))

        assert len(manager._dawn_check_cache) <= 3
        assert manager.get_cached_result(("loc0", "prev0", "curr0")) is None
        assert manager.get_cached_result(("loc4", "prev4", "curr4")) == (True, None)


class TestCacheManagerIsCacheEmpty:
    """Tests for CacheManager.is_cache_empty."""

    def test_is_cache_empty_when_new(self) -> None:
        """New cache manager should be empty."""
        manager = CacheManager()

        assert manager.is_cache_empty() is True

    def test_is_cache_empty_after_insert(self) -> None:
        """Cache should not be empty after inserting."""
        manager = CacheManager()
        manager.cache_result(("a", "b", "c"), (True, None))

        assert manager.is_cache_empty() is False
