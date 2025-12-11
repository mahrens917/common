import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from websockets import WebSocketException

from common.websocket_connection_manager_helpers.connection_lifecycle_helpers import (
    connection_establisher,
)


class TestConnectionEstablisher:
    @pytest.fixture
    def mock_websocket_connection(self):
        conn = AsyncMock()
        conn.close_code = None
        # In actual code, _already_cleaned is ONLY set on ConnectionError.
        # On success, it should not be present. We need to explicitly delete it if it somehow exists.
        if hasattr(conn, "_already_cleaned"):
            del conn._already_cleaned
        return conn

    @pytest.mark.asyncio
    async def test_connect_with_factory_success(self, mock_websocket_connection):
        factory = AsyncMock(return_value=mock_websocket_connection)

        conn = await connection_establisher.connect_with_factory(factory, 5, "test_service")

        assert conn == mock_websocket_connection
        factory.assert_called_once()
        assert not hasattr(conn, "_already_cleaned")  # Ensure it's explicitly not there

    @pytest.mark.asyncio
    async def test_connect_with_factory_none_returned(self):
        factory = AsyncMock(return_value=None)

        with pytest.raises(ConnectionError, match="WebSocket connection factory failed"):
            await connection_establisher.connect_with_factory(factory, 5, "test_service")

    @pytest.mark.asyncio
    async def test_connect_with_factory_closed_during_init(self, mock_websocket_connection):
        mock_websocket_connection.close_code = 1000
        factory = AsyncMock(return_value=mock_websocket_connection)

        with pytest.raises(ConnectionError, match="WebSocket connection closed during initialization"):
            await connection_establisher.connect_with_factory(factory, 5, "test_service")

    @pytest.mark.asyncio
    async def test_connect_with_factory_timeout(self):
        async def slow_factory():
            # Await to ensure it's a real coroutine that can be cancelled/timed out
            await asyncio.sleep(10)  # Longer than timeout.
            return Mock()

        with pytest.raises(TimeoutError, match="WebSocket connection timeout for test_service"):
            await connection_establisher.connect_with_factory(slow_factory, 0.01, "test_service")

    @pytest.mark.asyncio
    async def test_connect_with_defaults_success(self, mock_websocket_connection):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_websocket_connection

            conn = await connection_establisher.connect_with_defaults("ws://test.com", 5)

            assert conn == mock_websocket_connection
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_defaults_timeout(self):
        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError

            with pytest.raises(asyncio.TimeoutError):
                await connection_establisher.connect_with_defaults("ws://test.com", 0.01)

    def test_handle_connection_error_timeout(self):
        logger_mock = Mock()
        exc = asyncio.TimeoutError()
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert isinstance(result_exc, TimeoutError)
        assert str(result_exc) == "WebSocket connection timeout for test_service"
        logger_mock.error.assert_called_once_with("WebSocket connection timeout")

    def test_handle_connection_error_websocket_exception(self):
        logger_mock = Mock()
        exc = WebSocketException("WS error")
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert isinstance(result_exc, ConnectionError)
        assert str(result_exc) == "WebSocket connection failed"
        logger_mock.error.assert_called_once_with("WebSocket connection error")

    def test_handle_connection_error_os_error(self):
        logger_mock = Mock()
        exc = OSError("OS error")
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert isinstance(result_exc, ConnectionError)
        assert str(result_exc) == "Transport error"
        logger_mock.error.assert_called_once_with("Transport error")

    def test_handle_connection_error_os_error_already_cleaned(self):
        logger_mock = Mock()
        exc = OSError("OS error")
        setattr(exc, "_already_cleaned", True)
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert result_exc == exc
        logger_mock.error.assert_not_called()

    def test_handle_connection_error_runtime_error(self):
        logger_mock = Mock()
        exc = RuntimeError("Runtime error")
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert isinstance(result_exc, ConnectionError)
        assert str(result_exc) == "Unexpected error"
        logger_mock.error.assert_called_once_with("Unexpected error")

    def test_handle_connection_error_other_exception(self):
        # Use a generic Exception to fall into the final catch-all for unexpected errors
        logger_mock = Mock()
        exc = Exception("Other generic error")
        result_exc = connection_establisher.handle_connection_error(exc, "test_service", logger_mock)
        assert isinstance(result_exc, ConnectionError)  # The catch-all converts it
        assert str(result_exc) == "Unexpected error"
        logger_mock.error.assert_called_once_with("Unexpected error")
