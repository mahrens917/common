import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from websockets import WebSocketException

from src.common.websocket_connection_manager_helpers.message_operations import (
    WebSocketMessageOperations,
)


class TestWebSocketMessageOperations:
    @pytest.fixture
    def connection_provider(self):
        provider = Mock()
        provider.get_connection = Mock()
        return provider

    @pytest.fixture
    def operations(self, connection_provider):
        return WebSocketMessageOperations("test_service", connection_provider)

    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.close_code = None
        return ws

    @pytest.mark.asyncio
    async def test_send_message_success(self, operations, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket

        result = await operations.send_message("Hello")

        assert result is True
        mock_websocket.send.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, operations, connection_provider):
        connection_provider.get_connection.return_value = None

        result = await operations.send_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_closed(self, operations, connection_provider, mock_websocket):
        mock_websocket.close_code = 1000
        connection_provider.get_connection.return_value = mock_websocket

        result = await operations.send_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_websocket_exception(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.send.side_effect = WebSocketException("WS Error")

        result = await operations.send_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_unexpected_error(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.send.side_effect = RuntimeError("Unexpected")

        result = await operations.send_message("Hello")

        assert result is False

    @pytest.mark.asyncio
    async def test_receive_message_success_str(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.recv.return_value = "World"

        result = await operations.receive_message()

        assert result == "World"
        mock_websocket.recv.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_message_success_bytes(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.recv.return_value = b"World"

        result = await operations.receive_message()

        assert result == "World"

    @pytest.mark.asyncio
    async def test_receive_message_not_connected(self, operations, connection_provider):
        connection_provider.get_connection.return_value = None

        result = await operations.receive_message()

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_message_closed(self, operations, connection_provider, mock_websocket):
        mock_websocket.close_code = 1000
        connection_provider.get_connection.return_value = mock_websocket

        result = await operations.receive_message()

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_message_timeout(self, operations, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.recv.side_effect = asyncio.TimeoutError

        result = await operations.receive_message(timeout=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_message_websocket_exception(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.recv.side_effect = WebSocketException("WS Error")

        result = await operations.receive_message()

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_message_unexpected_error(
        self, operations, connection_provider, mock_websocket
    ):
        connection_provider.get_connection.return_value = mock_websocket
        mock_websocket.recv.side_effect = RuntimeError("Unexpected")

        result = await operations.receive_message()

        assert result is None
