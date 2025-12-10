"""Tests for WebSocket connection lifecycle helper."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from websockets import WebSocketException

from common.websocket_connection_manager_helpers import connection_lifecycle


class DummyConnection:
    def __init__(self, close_code=None):
        self.close_code = close_code
        self.close = AsyncMock()


def make_lifecycle(connection_factory=None):
    return connection_lifecycle.WebSocketConnectionLifecycle(
        "svc",
        "ws://url",
        connection_timeout=1.0,
        connection_factory=connection_factory,
    )


@pytest.mark.asyncio
async def test_establish_connection_success(monkeypatch):
    lifecycle = make_lifecycle()
    conn = DummyConnection()
    monkeypatch.setattr(
        connection_lifecycle,
        "_open_websocket",
        AsyncMock(return_value=conn),
    )
    monkeypatch.setattr(connection_lifecycle, "_validate_connection", MagicMock())
    cleanup = AsyncMock()
    monkeypatch.setattr(connection_lifecycle, "_cleanup_connection", cleanup)
    monkeypatch.setattr(
        connection_lifecycle.WebSocketConnectionLifecycle,
        "cleanup_connection",
        cleanup,
    )

    result = await lifecycle.establish_connection()

    assert result
    assert lifecycle.websocket_connection is conn
    cleanup.assert_not_awaited()


@pytest.mark.asyncio
async def test_establish_connection_timeout(monkeypatch):
    lifecycle = make_lifecycle()
    monkeypatch.setattr(
        connection_lifecycle,
        "_open_websocket",
        AsyncMock(side_effect=asyncio.TimeoutError()),
    )
    cleanup = AsyncMock()
    monkeypatch.setattr(connection_lifecycle, "_cleanup_connection", cleanup)
    monkeypatch.setattr(
        connection_lifecycle.WebSocketConnectionLifecycle,
        "cleanup_connection",
        cleanup,
    )

    with pytest.raises(TimeoutError):
        await lifecycle.establish_connection()

    cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_establish_connection_websocket_error(monkeypatch):
    lifecycle = make_lifecycle()
    monkeypatch.setattr(
        connection_lifecycle,
        "_open_websocket",
        AsyncMock(side_effect=WebSocketException("boom")),
    )
    cleanup = AsyncMock()
    monkeypatch.setattr(connection_lifecycle, "_cleanup_connection", cleanup)
    monkeypatch.setattr(
        connection_lifecycle.WebSocketConnectionLifecycle,
        "cleanup_connection",
        cleanup,
    )

    with pytest.raises(ConnectionError):
        await lifecycle.establish_connection()

    cleanup.assert_awaited_once()


def test_validate_connection_raises_for_closed():
    with pytest.raises(ConnectionError):
        connection_lifecycle._validate_connection(DummyConnection(close_code=100), "svc")

    with pytest.raises(ConnectionError):
        connection_lifecycle._validate_connection(None, "svc")


@pytest.mark.asyncio
async def test_cleanup_connection_closes(monkeypatch):
    lifecycle = make_lifecycle()
    conn = DummyConnection()
    lifecycle.websocket_connection = conn

    await lifecycle.cleanup_connection()

    conn.close.assert_awaited_once()
    assert lifecycle.websocket_connection is None
