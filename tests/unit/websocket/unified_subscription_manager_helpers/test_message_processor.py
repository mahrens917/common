from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.redis_protocol import SubscriptionUpdate
from common.websocket.unified_subscription_manager_helpers.message_processor import (
    MessageProcessor,
)


class TestMessageProcessor:
    @pytest.fixture
    def processor(self):
        return MessageProcessor(
            "test_service",
            update_handler=Mock(handle_update=AsyncMock()),
            subscription_processor=Mock(process_pending=AsyncMock()),
            health_validator=Mock(validate_health=AsyncMock()),
        )

    @pytest.mark.asyncio
    async def test_process_message_valid(self, processor):
        message = {
            "type": "message",
            "data": '{"name": "sub1", "action": "subscribe", "subscription_type": "type1"}',
        }
        redis_client = Mock()

        await processor.process_message(message, redis_client)

        processor.update_handler.handle_update.assert_called_once()
        processor.subscription_processor.process_pending.assert_called_once()
        processor.health_validator.validate_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_invalid_type(self, processor):
        message = {"type": "subscribe", "data": "..."}
        await processor.process_message(message, None)
        processor.update_handler.handle_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_invalid_data(self, processor):
        message = {"type": "message", "data": None}
        await processor.process_message(message, None)
        processor.update_handler.handle_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_parse_error(self, processor):
        message = {"type": "message", "data": "invalid json"}

        with patch("common.websocket.unified_subscription_manager_helpers.message_processor.logger") as mock_logger:
            await processor.process_message(message, None)
            mock_logger.exception.assert_called_once()

        processor.update_handler.handle_update.assert_not_called()

    def test_parse_update_success(self, processor):
        data = '{"name": "sub1", "action": "subscribe", "subscription_type": "type1"}'
        update = processor._parse_update(data)
        assert isinstance(update, SubscriptionUpdate)
        assert update.name == "sub1"

    def test_parse_update_failure(self, processor):
        assert processor._parse_update("invalid") is None
