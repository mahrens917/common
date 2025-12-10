from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.exceptions

from common.redis_protocol.persistence_manager import (
    RedisPersistenceManager,
    ensure_redis_persistence,
    get_redis_persistence_status,
)


class TestRedisPersistenceManager:
    @pytest.fixture
    def mock_deps(self):
        deps = MagicMock()
        deps.connection = AsyncMock()
        deps.connection.get_redis.return_value = AsyncMock()
        deps.configorchestrator = AsyncMock()
        deps.snapshot = AsyncMock()
        deps.keyscanner = AsyncMock()
        deps.dataserializer = MagicMock()
        deps.validation = MagicMock()
        return deps

    @pytest.fixture
    def manager(self, mock_deps):
        return RedisPersistenceManager(dependencies=mock_deps)

    @pytest.mark.asyncio
    async def test_initialize(self, manager, mock_deps):
        await manager.initialize()
        mock_deps.connection.ensure_connection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close(self, manager, mock_deps):
        await manager.close()
        mock_deps.connection.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_configure_persistence(self, manager, mock_deps):
        mock_deps.configorchestrator.configure_all.return_value = True
        result = await manager.configure_persistence()
        assert result is True
        mock_deps.configorchestrator.configure_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_persistence_status_success(self, manager, mock_deps):
        mock_deps.keyscanner.get_config_info.return_value = {"config": 1}
        mock_deps.keyscanner.get_persistence_info.return_value = {"persist": 1}
        mock_deps.snapshot.get_last_save_time.return_value = 123
        mock_deps.dataserializer.build_status_dict.return_value = {"status": "ok"}

        status = await manager.check_persistence_status()
        assert status == {"status": "ok"}

        mock_deps.dataserializer.build_status_dict.assert_called_with(
            {"config": 1}, {"persist": 1}, 123
        )

    @pytest.mark.asyncio
    async def test_check_persistence_status_error(self, manager, mock_deps):
        mock_deps.keyscanner.get_config_info.side_effect = redis.exceptions.RedisError("Fail")

        status = await manager.check_persistence_status()
        assert "error" in status
        assert status["error"] == "Fail"

    @pytest.mark.asyncio
    async def test_validate_persistence_valid(self, manager, mock_deps):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.return_value = {"status": "ok"}
            mock_deps.validation.validate_status.return_value = (True, "Valid")

            is_valid, msg = await manager.validate_persistence()
            assert is_valid is True
            assert msg == "Valid"

    @pytest.mark.asyncio
    async def test_validate_persistence_exception(self, manager):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.side_effect = ValueError("Error")

            is_valid, msg = await manager.validate_persistence()
            assert is_valid is False
            assert "Error validating" in msg

    @pytest.mark.asyncio
    async def test_validate_persistence_redis_exception(self, manager):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.side_effect = redis.exceptions.RedisError("Redis Error")

            is_valid, msg = await manager.validate_persistence()
            assert is_valid is False
            assert "Redis error validating" in msg

    @pytest.mark.asyncio
    async def test_get_persistence_info_success(self, manager, mock_deps):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.return_value = {"status": "ok"}
            mock_deps.dataserializer.format_persistence_status.return_value = "Formatted Info"

            info = await manager.get_persistence_info()
            assert info == "Formatted Info"

    @pytest.mark.asyncio
    async def test_get_persistence_info_exception(self, manager):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.side_effect = ValueError("Error")

            info = await manager.get_persistence_info()
            assert "Error getting persistence info" in info

    @pytest.mark.asyncio
    async def test_get_persistence_info_redis_exception(self, manager):
        with patch.object(manager, "check_persistence_status") as mock_check:
            mock_check.side_effect = redis.exceptions.RedisError("Redis Error")

            info = await manager.get_persistence_info()
            assert "Redis error getting persistence info" in info


class TestModuleFunctions:
    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_success(self):
        with patch(
            "common.redis_protocol.persistence_manager.RedisPersistenceManager"
        ) as MockManager:
            manager = MockManager.return_value
            manager.initialize = AsyncMock()
            manager.close = AsyncMock()
            manager.validate_persistence = AsyncMock(return_value=(True, "OK"))

            assert await ensure_redis_persistence() is True
            manager.configure_persistence.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_needs_config(self):
        with patch(
            "common.redis_protocol.persistence_manager.RedisPersistenceManager"
        ) as MockManager:
            manager = MockManager.return_value
            manager.initialize = AsyncMock()
            manager.close = AsyncMock()
            manager.validate_persistence = AsyncMock(
                side_effect=[(False, "Not Configured"), (True, "OK")]
            )
            manager.configure_persistence = AsyncMock(return_value=True)

            assert await ensure_redis_persistence() is True
            manager.configure_persistence.assert_awaited()

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_config_fails(self):
        with patch(
            "common.redis_protocol.persistence_manager.RedisPersistenceManager"
        ) as MockManager:
            manager = MockManager.return_value
            manager.initialize = AsyncMock()
            manager.close = AsyncMock()
            manager.validate_persistence = AsyncMock(return_value=(False, "Not Configured"))
            manager.configure_persistence = AsyncMock(return_value=False)

            assert await ensure_redis_persistence() is False

    @pytest.mark.asyncio
    async def test_get_redis_persistence_status(self):
        with patch(
            "common.redis_protocol.persistence_manager.RedisPersistenceManager"
        ) as MockManager:
            manager = MockManager.return_value
            manager.initialize = AsyncMock()
            manager.close = AsyncMock()
            manager.check_persistence_status = AsyncMock(return_value={"status": "ok"})

            assert await get_redis_persistence_status() == {"status": "ok"}
