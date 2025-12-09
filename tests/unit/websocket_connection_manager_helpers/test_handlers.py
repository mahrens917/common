"""Tests for websocket connection manager helper stubs."""

import pytest

from src.common.websocket_connection_manager_helpers import (
    message_handler,
    ping_pong_manager,
    ws_connection_handler,
)


class DummyMessageHandler(message_handler.MessageHandler):
    async def handle_message(self, *args, **kwargs):
        return "message"


class DummyPingPongManager(ping_pong_manager.PingPongManager):
    async def manage_ping_pong(self, *args, **kwargs):
        return "pong"


class DummyConnectionHandler(ws_connection_handler.WsConnectionHandler):
    async def handle_connection(self, *args, **kwargs):
        return "connection"


@pytest.mark.asyncio
async def test_message_handler_stores_kwargs():
    handler = DummyMessageHandler(extra="value")
    assert handler.extra == "value"
    assert await handler.handle_message() == "message"
    handler.request_shutdown()
    assert handler._shutdown_requested


@pytest.mark.asyncio
async def test_ping_pong_manager_stub_raises_when_not_implemented():
    manager = ping_pong_manager.PingPongManager()
    with pytest.raises(NotImplementedError):
        await manager.manage_ping_pong()


@pytest.mark.asyncio
async def test_ping_pong_manager_handles_call():
    manager = DummyPingPongManager(extra="value")
    assert await manager.manage_ping_pong() == "pong"


@pytest.mark.asyncio
async def test_ws_connection_handler_stub_raises():
    handler = ws_connection_handler.WsConnectionHandler()
    with pytest.raises(NotImplementedError):
        await handler.handle_connection()


@pytest.mark.asyncio
async def test_ws_connection_handler_sets_kwargs():
    handler = DummyConnectionHandler(name="ws")
    assert handler.name == "ws"
    handler.request_shutdown()
    assert handler._shutdown_requested
