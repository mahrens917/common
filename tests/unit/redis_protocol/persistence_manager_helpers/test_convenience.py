from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.redis_protocol.persistence_manager_helpers.convenience import (
    ensure_redis_persistence,
    get_redis_persistence_status,
)


class TestConvenience:
    @pytest.fixture
    def mock_manager(self):
        with patch(
            "common.redis_protocol.persistence_manager.RedisPersistenceManager"
        ) as MockManager:
            manager = AsyncMock()
            MockManager.return_value = manager
            yield manager

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_already_configured(self, mock_manager):
        """Test ensure_redis_persistence when already configured."""
        mock_manager.validate_persistence.return_value = (True, "OK")

        assert await ensure_redis_persistence() is True
        mock_manager.initialize.assert_awaited_once()
        mock_manager.configure_persistence.assert_not_awaited()
        mock_manager.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_configure_success(self, mock_manager):
        """Test ensure_redis_persistence needs configuration and succeeds."""
        mock_manager.validate_persistence.side_effect = [(False, "Not config"), (True, "OK")]
        mock_manager.configure_persistence.return_value = True

        assert await ensure_redis_persistence() is True
        mock_manager.configure_persistence.assert_awaited_once()
        assert mock_manager.validate_persistence.await_count == 2

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_configure_fails(self, mock_manager):
        """Test ensure_redis_persistence fails to configure."""
        mock_manager.validate_persistence.return_value = (False, "Not config")
        mock_manager.configure_persistence.return_value = False

        assert await ensure_redis_persistence() is False
        mock_manager.configure_persistence.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_redis_persistence_validation_fails_after_config(self, mock_manager):
        """Test ensure_redis_persistence configures but validation still fails."""
        mock_manager.validate_persistence.side_effect = [
            (False, "Not config"),
            (False, "Still fail"),
        ]
        mock_manager.configure_persistence.return_value = True

        assert await ensure_redis_persistence() is False
        mock_manager.configure_persistence.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_redis_persistence_status(self, mock_manager):
        """Test get_redis_persistence_status."""
        mock_manager.get_persistence_info.return_value = "Status Info"

        assert await get_redis_persistence_status() == "Status Info"
        mock_manager.initialize.assert_awaited_once()
        mock_manager.get_persistence_info.assert_awaited_once()
        mock_manager.close.assert_awaited_once()
