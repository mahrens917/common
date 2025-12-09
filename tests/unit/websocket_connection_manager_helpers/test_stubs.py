"""Tests for websocket connection manager helper stubs."""

import pytest

from src.common.websocket_connection_manager_helpers.message_handler import MessageHandler
from src.common.websocket_connection_manager_helpers.ping_pong_manager import PingPongManager
from src.common.websocket_connection_manager_helpers.ws_connection_handler import (
    WsConnectionHandler,
)


@pytest.mark.asyncio
async def test_message_handler_basic():
    handler = MessageHandler(foo="bar")
    assert handler.foo == "bar"
    handler.request_shutdown()
    assert handler._shutdown_requested
    with pytest.raises(NotImplementedError):
        await handler.handle_message()


@pytest.mark.asyncio
async def test_ping_pong_manager_basic():
    manager = PingPongManager(foo="bar")
    assert manager.foo == "bar"
    manager.request_shutdown()
    assert manager._shutdown_requested
    with pytest.raises(NotImplementedError):
        await manager.manage_ping_pong()


@pytest.mark.asyncio
async def test_ws_connection_handler_basic():
    handler = WsConnectionHandler(foo="bar")
    assert handler.foo == "bar"
    handler.request_shutdown()
    assert handler._shutdown_requested
    with pytest.raises(NotImplementedError):
        await handler.handle_connection()
