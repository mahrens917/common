import asyncio
import contextlib
from unittest.mock import AsyncMock

import pytest
from websockets import WebSocketException

from common.connection_state import ConnectionState
from common.websocket_connection_manager import WebSocketConnectionManager

DEFAULT_WEBSOCKET_CONNECTION_TIMEOUT_SECONDS = 0.5
DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS = 0.01


class DummyAlerter:
    async def send_alert(self, *args, **kwargs):
        return None


class DummyConnection:
    def __init__(
        self,
        close_code=None,
        recv_messages=None,
        recv_delay=0.0,
        ping_should_timeout=False,
        send_exception=None,
        recv_exception=None,
        close_exception=None,
    ):
        self.close_code = close_code
        self.sent_messages = []
        self.ping_calls = 0
        self.closed = False
        self.local_address = ("127.0.0.1", 0)
        self.remote_address = ("10.0.0.1", 0)
        self._ping_should_timeout = ping_should_timeout
        self.recv_messages = list(recv_messages or [])
        self._recv_delay = recv_delay
        self._send_exception = send_exception
        self._recv_exception = recv_exception
        self._close_exception = close_exception

    async def ping(self):
        self.ping_calls += 1
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        if not self._ping_should_timeout:
            future.set_result(None)
        return future

    async def close(self):
        if self._close_exception:
            raise self._close_exception
        self.closed = True

    async def send(self, message):
        if self._send_exception:
            raise self._send_exception
        self.sent_messages.append(message)

    async def recv(self):
        if self._recv_exception:
            raise self._recv_exception
        if self._recv_delay:
            await asyncio.sleep(self._recv_delay)
        if self.recv_messages:
            return self.recv_messages.pop(0)
        return "message"


def make_manager(**kwargs):
    manager = WebSocketConnectionManager(
        "kalshi",
        "wss://example",
        alerter=DummyAlerter(),
        **kwargs,
    )
    manager.config.connection_timeout_seconds = DEFAULT_WEBSOCKET_CONNECTION_TIMEOUT_SECONDS
    return manager


@pytest.mark.asyncio
async def test_establish_connection_with_factory_success():
    connection = DummyConnection()

    async def factory():
        return connection

    manager = make_manager(connection_factory=factory)
    assert await manager.establish_connection() is True
    assert manager.websocket_connection is connection


@pytest.mark.asyncio
async def test_establish_connection_raises_when_closed(monkeypatch):
    connection = DummyConnection(close_code=1000)

    async def factory():
        return connection

    manager = make_manager(connection_factory=factory)
    manager.cleanup_connection = AsyncMock()

    with pytest.raises(ConnectionError):
        await manager.establish_connection()

    manager.cleanup_connection.assert_awaited_once()


@pytest.mark.asyncio
async def test_establish_connection_uses_websockets_connect(monkeypatch):
    connection = DummyConnection()

    async def fake_connect(*args, **kwargs):
        return connection

    monkeypatch.setattr("common.websocket_connection_manager.websockets.connect", fake_connect)

    manager = make_manager()
    assert await manager.establish_connection() is True
    assert manager.websocket_connection is connection


@pytest.mark.asyncio
async def test_establish_connection_timeout_raises(monkeypatch):
    async def factory():
        return DummyConnection()

    async def fake_wait_for(awaitable, timeout):
        task = asyncio.create_task(awaitable)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        raise asyncio.TimeoutError

    manager = make_manager(connection_factory=factory)
    monkeypatch.setattr("common.websocket_connection_manager.asyncio.wait_for", fake_wait_for)

    with pytest.raises(TimeoutError):
        await manager.establish_connection()


@pytest.mark.asyncio
async def test_establish_connection_wraps_websocket_exception(monkeypatch):
    async def factory():
        raise WebSocketException("boom")

    manager = make_manager(connection_factory=factory)

    with pytest.raises(ConnectionError):
        await manager.establish_connection()


@pytest.mark.asyncio
async def test_establish_connection_wraps_unexpected_exception(monkeypatch):
    async def factory():
        raise RuntimeError("unexpected")

    manager = make_manager(connection_factory=factory)

    with pytest.raises(ConnectionError):
        await manager.establish_connection()


@pytest.mark.asyncio
async def test_check_connection_health_sends_ping(monkeypatch):
    connection = DummyConnection()
    manager = make_manager()
    manager.websocket_connection = connection
    manager.health_monitor.ping_interval_seconds = 0
    manager.health_monitor.last_ping_time = 0
    manager.health_monitor.last_pong_time = 0

    result = await manager.check_connection_health()
    assert result.healthy is True
    assert connection.ping_calls == 1


@pytest.mark.asyncio
async def test_check_connection_health_returns_false_on_timeout():
    connection = DummyConnection()
    connection._ping_should_timeout = True

    manager = make_manager()
    manager.websocket_connection = connection
    manager.health_monitor.ping_interval_seconds = 0
    manager.health_monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS

    result = await manager.check_connection_health()
    assert result.healthy is False


@pytest.mark.asyncio
async def test_check_connection_health_detects_closed_connection():
    connection = DummyConnection(close_code=1000)
    manager = make_manager()
    manager.websocket_connection = connection

    assert (await manager.check_connection_health()).healthy is False


@pytest.mark.asyncio
async def test_check_connection_health_handles_missing_connection():
    manager = make_manager()
    manager.websocket_connection = None
    assert (await manager.check_connection_health()).healthy is False


@pytest.mark.asyncio
async def test_check_connection_health_detects_stale_pong():
    connection = DummyConnection()
    manager = make_manager()
    manager.websocket_connection = connection
    loop = asyncio.get_running_loop()
    now = loop.time()
    manager.health_monitor.last_ping_time = now
    manager.health_monitor.last_pong_time = now - (
        manager.health_monitor.ping_interval_seconds * 2 + 5
    )

    assert (await manager.check_connection_health()).healthy is False


@pytest.mark.asyncio
async def test_cleanup_connection_closes_active_connection():
    connection = DummyConnection()
    manager = make_manager()
    manager.websocket_connection = connection

    await manager.cleanup_connection()

    assert connection.closed is True
    assert manager.websocket_connection is None


@pytest.mark.asyncio
async def test_cleanup_connection_handles_already_closed():
    connection = DummyConnection(close_code=1000)
    manager = make_manager()
    manager.websocket_connection = connection

    await manager.cleanup_connection()
    assert manager.websocket_connection is None


@pytest.mark.asyncio
async def test_cleanup_connection_logs_errors(monkeypatch):
    connection = DummyConnection(close_exception=RuntimeError("close failure"))
    manager = make_manager()
    manager.websocket_connection = connection

    await manager.cleanup_connection()
    assert manager.websocket_connection is None


@pytest.mark.asyncio
async def test_send_message_success():
    connection = DummyConnection()
    manager = make_manager()
    manager.websocket_connection = connection

    result = await manager.send_message("hello")
    assert result is True
    assert connection.sent_messages == ["hello"]


@pytest.mark.asyncio
async def test_send_message_handles_websocket_error():
    connection = DummyConnection(send_exception=WebSocketException("send failed"))
    manager = make_manager()
    manager.websocket_connection = connection

    assert await manager.send_message("hello") is False


@pytest.mark.asyncio
async def test_send_message_fails_when_not_connected():
    manager = make_manager()
    manager.websocket_connection = None
    assert await manager.send_message("hello") is False


@pytest.mark.asyncio
async def test_receive_message_returns_payload():
    connection = DummyConnection(recv_messages=["payload"])
    manager = make_manager()
    manager.websocket_connection = connection

    message = await manager.receive_message()
    assert message == "payload"


@pytest.mark.asyncio
async def test_receive_message_decodes_bytes():
    connection = DummyConnection(recv_messages=[b"bytes"])
    manager = make_manager()
    manager.websocket_connection = connection

    message = await manager.receive_message()
    assert message == "bytes"


@pytest.mark.asyncio
async def test_receive_message_handles_websocket_error():
    connection = DummyConnection(recv_exception=WebSocketException("recv failed"))
    manager = make_manager()
    manager.websocket_connection = connection

    assert await manager.receive_message() is None


@pytest.mark.asyncio
async def test_receive_message_timeout_returns_none():
    connection = DummyConnection(recv_messages=["slow"], recv_delay=0.1)
    manager = make_manager()
    manager.websocket_connection = connection

    message = await manager.receive_message(timeout=0.01)
    assert message is None


def test_is_connected_and_connection_info():
    connection = DummyConnection()
    manager = make_manager()
    manager.websocket_connection = connection

    assert manager.is_connected() is True

    info = manager.get_connection_info()
    assert info["state"] == ConnectionState.DISCONNECTED.value
    assert info["websocket_details"]["is_connected"] is True


def test_get_connection_info_without_connection():
    manager = make_manager()
    info = manager.get_connection_info()
    assert info["websocket_details"]["is_connected"] is False
