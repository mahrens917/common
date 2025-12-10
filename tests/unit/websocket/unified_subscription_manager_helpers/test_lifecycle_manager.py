import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from common.websocket.unified_subscription_manager_helpers.lifecycle_manager import (
    LifecycleManager,
)


class TestLifecycleManager:
    @pytest.fixture
    def manager(self):
        return LifecycleManager("test_service")

    @pytest.mark.asyncio
    async def test_start_monitoring(self, manager):
        coro = AsyncMock()
        await manager.start_monitoring(coro())

        assert manager.is_monitoring()
        assert manager._monitoring_task is not None

        # Cleanup
        await manager.stop_monitoring()

    @pytest.mark.asyncio
    async def test_start_monitoring_already_started(self, manager):
        manager._monitoring_task = AsyncMock()

        with patch(
            "common.websocket.unified_subscription_manager_helpers.lifecycle_manager.logger"
        ) as mock_logger:
            await manager.start_monitoring(AsyncMock()())
            mock_logger.warning.assert_called_with(
                "test_service subscription monitoring already started"
            )

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, manager):
        # Create a dummy task
        async def dummy():
            await asyncio.sleep(0)

        await manager.start_monitoring(dummy())
        assert manager.is_monitoring()

        await manager.stop_monitoring()
        assert not manager.is_monitoring()
        assert manager._monitoring_task is None

    def test_is_monitoring(self, manager):
        assert not manager.is_monitoring()
        manager._monitoring_task = AsyncMock()
        assert manager.is_monitoring()
