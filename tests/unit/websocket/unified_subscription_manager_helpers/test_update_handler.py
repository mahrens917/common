from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.unified_subscription_manager_helpers.update_handler import UpdateHandler


class TestUpdateHandler:
    @pytest.fixture
    def handler(self):
        websocket_client = Mock()
        websocket_client.unsubscribe = AsyncMock()
        websocket_client.active_subscriptions = {}

        return UpdateHandler(
            "test_service",
            websocket_client,
            active_instruments={},
            pending_subscriptions=[],
            api_type_mapper=lambda x: x,
        )

    @pytest.mark.asyncio
    async def test_handle_update_subscribe(self, handler):
        update = Mock()
        update.name = "sub1"
        update.action = "subscribe"
        update.subscription_type = "type1"

        await handler.handle_update(update, None)

        assert len(handler.pending_subscriptions) == 1
        assert handler.pending_subscriptions[0] == ("sub1", "type1", "sub1")

    @pytest.mark.asyncio
    async def test_handle_update_subscribe_existing(self, handler):
        handler.active_instruments["sub1"] = {}
        update = Mock()
        update.name = "sub1"
        update.action = "subscribe"
        update.subscription_type = "type1"

        await handler.handle_update(update, None)

        assert len(handler.pending_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_handle_update_unsubscribe_success(self, handler):
        handler.active_instruments["sub1"] = {}
        update = Mock()
        update.name = "sub1"
        update.action = "unsubscribe"
        update.subscription_type = "type1"

        await handler.handle_update(update, None)

        handler.websocket_client.unsubscribe.assert_called_once_with(["sub1"])
        assert "sub1" not in handler.active_instruments

    @pytest.mark.asyncio
    async def test_handle_update_unsubscribe_failure(self, handler):
        handler.active_instruments["sub1"] = {}
        # Mock client still having subscription after unsubscribe
        handler.websocket_client.active_subscriptions = {"sub1": {}}

        update = Mock()
        update.name = "sub1"
        update.action = "unsubscribe"
        update.subscription_type = "type1"

        await handler.handle_update(update, None)

        handler.websocket_client.unsubscribe.assert_called_once()
        assert "sub1" in handler.active_instruments

    @pytest.mark.asyncio
    async def test_handle_update_unsubscribe_exception(self, handler):
        handler.active_instruments["sub1"] = {}
        handler.websocket_client.unsubscribe.side_effect = ValueError("Fail")

        update = Mock()
        update.name = "sub1"
        update.action = "unsubscribe"
        update.subscription_type = "type1"

        # Should catch exception and not raise
        await handler.handle_update(update, None)
