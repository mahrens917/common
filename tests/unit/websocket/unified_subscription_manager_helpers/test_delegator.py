from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.unified_subscription_manager_helpers.delegator import (
    UnifiedSubscriptionManagerDelegator,
)


class TestUnifiedSubscriptionManagerDelegator:
    @pytest.fixture
    def delegator(self):
        with patch(
            "common.websocket.unified_subscription_manager_helpers.factory.UnifiedSubscriptionManagerFactory.create_components"
        ) as mock_factory:
            lifecycle_manager = Mock()
            monitoring_loop = Mock()
            mock_factory.return_value = (lifecycle_manager, monitoring_loop)

            return UnifiedSubscriptionManagerDelegator("service", Mock(), "chan", {}, [], Mock())

    @pytest.mark.asyncio
    async def test_start_monitoring(self, delegator):
        delegator.lifecycle_manager.start_monitoring = AsyncMock()
        delegator.monitoring_loop.run = Mock(return_value="coro")

        await delegator.start_monitoring()

        delegator.monitoring_loop.run.assert_called_once()
        delegator.lifecycle_manager.start_monitoring.assert_called_once_with("coro")

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, delegator):
        delegator.lifecycle_manager.stop_monitoring = AsyncMock()

        await delegator.stop_monitoring()

        delegator.lifecycle_manager.stop_monitoring.assert_called_once()
