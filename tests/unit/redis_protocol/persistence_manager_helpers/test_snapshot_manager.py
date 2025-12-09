from unittest.mock import AsyncMock, Mock

import pytest

from src.common.redis_protocol.error_types import RedisError
from src.common.redis_protocol.persistence_manager_helpers.snapshot_manager import SnapshotManager


class TestSnapshotManager:
    @pytest.mark.asyncio
    async def test_force_background_save_success(self):
        redis = AsyncMock()
        manager = SnapshotManager()

        result = await manager.force_background_save(redis)
        assert result is True
        redis.bgsave.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_background_save_failure(self):
        redis = AsyncMock()
        redis.bgsave.side_effect = RedisError("Failed")
        manager = SnapshotManager()

        result = await manager.force_background_save(redis)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_last_save_time(self):
        redis = AsyncMock()
        redis.lastsave.return_value = 12345
        manager = SnapshotManager()

        result = await manager.get_last_save_time(redis)
        assert result == 12345

    @pytest.mark.asyncio
    async def test_configure_save_points_success(self):
        redis = AsyncMock()
        manager = SnapshotManager()

        result = await manager.configure_save_points(redis, "900 1 300 10")
        assert result is True

        # Should clear first then set
        assert redis.config_set.call_count == 3  # 1 clear + 2 sets
        redis.config_set.assert_any_call("save", "")
        redis.config_set.assert_any_call("save", "900 1")
        redis.config_set.assert_any_call("save", "300 10")

    @pytest.mark.asyncio
    async def test_configure_save_points_failure(self):
        redis = AsyncMock()
        redis.config_set.side_effect = RedisError("Failed")
        manager = SnapshotManager()

        result = await manager.configure_save_points(redis, "900 1")
        assert result is False
