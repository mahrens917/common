from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.subscription_manager import UnifiedSubscriptionManager


class TestUnifiedSubscriptionManager:
    @pytest.fixture
    def manager(self):
        websocket_client = Mock()
        return UnifiedSubscriptionManager(
            "test_service", websocket_client, "test_channel", "test_key"
        )

    @pytest.mark.asyncio
    async def test_start_monitoring(self, manager):
        manager._delegator = Mock()
        manager._delegator.start_monitoring = AsyncMock()

        await manager.start_monitoring()

        manager._delegator.start_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, manager):
        manager._delegator = Mock()
        manager._delegator.stop_monitoring = AsyncMock()

        await manager.stop_monitoring()

        manager._delegator.stop_monitoring.assert_called_once()

    def test_get_api_type(self, manager):
        assert manager._get_api_type("type1") == "type1"
