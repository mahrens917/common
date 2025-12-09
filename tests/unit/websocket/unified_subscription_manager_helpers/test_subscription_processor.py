from unittest.mock import AsyncMock, Mock

import pytest

from src.common.websocket.unified_subscription_manager_helpers.subscription_processor import (
    SubscriptionProcessor,
)


class TestSubscriptionProcessor:
    @pytest.fixture
    def websocket_client(self):
        client = Mock()
        client.is_connected = True
        client.subscribe = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def processor(self, websocket_client):
        return SubscriptionProcessor(
            "test_service", websocket_client, active_instruments={}, pending_subscriptions=[]
        )

    @pytest.mark.asyncio
    async def test_process_pending_no_subscriptions(self, processor):
        await processor.process_pending()
        processor.websocket_client.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_pending_not_connected(self, processor):
        processor.pending_subscriptions.append(("key", "type", "chan"))
        processor.websocket_client.is_connected = False

        await processor.process_pending()
        processor.websocket_client.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_pending_success(self, processor):
        processor.pending_subscriptions.append(("key", "type", "chan"))

        await processor.process_pending()

        processor.websocket_client.subscribe.assert_called_once_with(["chan"])
        assert "key" in processor.active_instruments
        assert len(processor.pending_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_process_pending_failure(self, processor):
        processor.pending_subscriptions.append(("key", "type", "chan"))
        processor.websocket_client.subscribe.return_value = False

        await processor.process_pending()

        processor.websocket_client.subscribe.assert_called_once()
        assert "key" not in processor.active_instruments
        # Pending subscriptions are cleared even on failure in current implementation?
        # Code: if channels_to_subscribe: ... if success: ... else: ... ; self.pending_subscriptions.clear()
        # Yes, they are cleared.
        assert len(processor.pending_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_process_pending_exception(self, processor):
        processor.pending_subscriptions.append(("key", "type", "chan"))
        processor.websocket_client.subscribe.side_effect = ValueError("Fail")

        # Should catch exception and not raise
        await processor.process_pending()

        assert processor.waiting_for_subscriptions is False
