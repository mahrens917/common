"""Tests for redis tracker module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.dependency_monitor_helpers.redis_tracker import (
    RedisTracker,
    _capture_async_result,
)


class TestCaptureAsyncResult:
    """Tests for _capture_async_result function."""

    @pytest.mark.asyncio
    async def test_returns_result_on_success(self) -> None:
        """Returns (result, None) on success."""

        async def successful_coro():
            return "success"

        result, error = await _capture_async_result(successful_coro())

        assert result == "success"
        assert error is None

    @pytest.mark.asyncio
    async def test_returns_error_on_exception(self) -> None:
        """Returns (None, error) on exception."""

        async def failing_coro():
            raise ValueError("test error")

        result, error = await _capture_async_result(failing_coro())

        assert result is None
        assert isinstance(error, ValueError)


class TestRedisTracker:
    """Tests for RedisTracker class."""

    def test_init_stores_service_name_and_redis(self) -> None:
        """Stores service_name and redis client."""
        redis = MagicMock()

        tracker = RedisTracker("test_service", redis)

        assert tracker.service_name == "test_service"
        assert tracker.redis == redis

    def test_init_accepts_none_redis(self) -> None:
        """Accepts None for redis client."""
        tracker = RedisTracker("test_service", None)

        assert tracker.redis is None


class TestInitializeDependencyTracking:
    """Tests for initialize_dependency_tracking method."""

    @pytest.mark.asyncio
    async def test_returns_early_when_no_redis(self) -> None:
        """Returns early when redis is None."""
        tracker = RedisTracker("test_service", None)

        await tracker.initialize_dependency_tracking(["dep1", "dep2"])

        # No error raised

    @pytest.mark.asyncio
    async def test_returns_early_when_no_dependencies(self) -> None:
        """Returns early when dependency list is empty."""
        redis = AsyncMock()
        tracker = RedisTracker("test_service", redis)

        await tracker.initialize_dependency_tracking([])

        redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_existing_dependencies_key(self) -> None:
        """Deletes existing dependencies key."""
        redis = AsyncMock()
        redis.delete.return_value = 1
        redis.sadd.return_value = 2
        redis.hset.return_value = 1
        tracker = RedisTracker("test_service", redis)

        await tracker.initialize_dependency_tracking(["dep1"])

        redis.delete.assert_called_once_with("service_dependencies:test_service")

    @pytest.mark.asyncio
    async def test_adds_dependency_names_to_set(self) -> None:
        """Adds dependency names to Redis set."""
        redis = AsyncMock()
        redis.delete.return_value = 1
        redis.sadd.return_value = 2
        redis.hset.return_value = 1
        tracker = RedisTracker("test_service", redis)

        await tracker.initialize_dependency_tracking(["dep1", "dep2"])

        redis.sadd.assert_called_once()
        call_args = redis.sadd.call_args
        assert "service_dependencies:test_service" in call_args[0]

    @pytest.mark.asyncio
    async def test_sets_initial_status_for_each_dependency(self) -> None:
        """Sets initial status for each dependency."""
        redis = AsyncMock()
        redis.delete.return_value = 1
        redis.sadd.return_value = 2
        redis.hset.return_value = 1
        tracker = RedisTracker("test_service", redis)

        await tracker.initialize_dependency_tracking(["dep1", "dep2"])

        assert redis.hset.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_delete_error(self) -> None:
        """Handles error during delete operation."""
        redis = AsyncMock()
        redis.delete.side_effect = Exception("delete error")
        tracker = RedisTracker("test_service", redis)

        # Should not raise, just log error
        await tracker.initialize_dependency_tracking(["dep1"])

    @pytest.mark.asyncio
    async def test_handles_sadd_error(self) -> None:
        """Handles error during sadd operation."""
        redis = AsyncMock()
        redis.delete.return_value = 1
        redis.sadd.side_effect = Exception("sadd error")
        tracker = RedisTracker("test_service", redis)

        # Should not raise, just log error
        await tracker.initialize_dependency_tracking(["dep1"])

    @pytest.mark.asyncio
    async def test_handles_hset_error(self) -> None:
        """Handles error during hset operation."""
        redis = AsyncMock()
        redis.delete.return_value = 1
        redis.sadd.return_value = 1
        redis.hset.side_effect = Exception("hset error")
        tracker = RedisTracker("test_service", redis)

        # Should not raise, just log error
        await tracker.initialize_dependency_tracking(["dep1"])


class TestUpdateDependencyStatus:
    """Tests for update_dependency_status method."""

    @pytest.mark.asyncio
    async def test_returns_early_when_no_redis(self) -> None:
        """Returns early when redis is None."""
        from common.dependency_monitor_helpers.dependency_checker import (
            DependencyStatus,
        )

        tracker = RedisTracker("test_service", None)

        await tracker.update_dependency_status("dep1", DependencyStatus.AVAILABLE)

        # No error raised

    @pytest.mark.asyncio
    async def test_updates_status_in_redis(self) -> None:
        """Updates dependency status in Redis hash."""
        from common.dependency_monitor_helpers.dependency_checker import (
            DependencyStatus,
        )

        redis = AsyncMock()
        redis.hset.return_value = 1
        tracker = RedisTracker("test_service", redis)

        await tracker.update_dependency_status("dep1", DependencyStatus.AVAILABLE)

        redis.hset.assert_called_once()
        call_args = redis.hset.call_args
        assert "dependency_status:test_service" in call_args[0]
        assert "dep1" in call_args[0]
        assert "available" in call_args[0]

    @pytest.mark.asyncio
    async def test_handles_hset_error(self) -> None:
        """Handles error during hset operation."""
        from common.dependency_monitor_helpers.dependency_checker import (
            DependencyStatus,
        )

        redis = AsyncMock()
        redis.hset.side_effect = Exception("hset error")
        tracker = RedisTracker("test_service", redis)

        # Should not raise, just log error
        await tracker.update_dependency_status("dep1", DependencyStatus.AVAILABLE)
