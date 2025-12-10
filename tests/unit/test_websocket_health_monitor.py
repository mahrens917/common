import asyncio

import pytest
from websockets import WebSocketException

from common.websocket_connection_manager_helpers.health_monitor import WebSocketHealthMonitor

DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS = 0.01


class DummyConnectionProvider:
    def __init__(self, websocket):
        self._websocket = websocket

    def get_connection(self):
        return self._websocket


class DummyWebSocket:
    def __init__(
        self,
        *,
        close_code=None,
        ping_should_timeout: bool = False,
        ping_exception: Exception | None = None,
    ):
        self.close_code = close_code
        self._ping_should_timeout = ping_should_timeout
        self._ping_exception = ping_exception
        self.ping_calls = 0

    async def ping(self):
        if self._ping_exception:
            raise self._ping_exception
        self.ping_calls += 1
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        if not self._ping_should_timeout:
            future.set_result(None)
        return future


@pytest.mark.asyncio
async def test_websocket_monitor_success_records_success():
    websocket = DummyWebSocket()
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 0
    monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS

    result = await monitor.check_health()

    assert result.healthy is True
    assert monitor.consecutive_failures == 0
    assert monitor.last_success_time > 0
    assert websocket.ping_calls == 1


@pytest.mark.asyncio
async def test_websocket_monitor_pong_timeout_records_failure():
    websocket = DummyWebSocket(ping_should_timeout=True)
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 0
    monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.error == "pong_timeout"
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_closed_connection_fails_fast():
    websocket = DummyWebSocket(close_code=1000)
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.error == "connection_closed"
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_connection_missing_records_failure():
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(None))

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.error == "connection_missing"
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_stale_pong_without_ping():
    websocket = DummyWebSocket()
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 10
    monitor.last_ping_time = 95.0
    monitor.last_pong_time = 60.0

    # Monkeypatching asyncio.get_running_loop via pytest is awkward inside async tests; use context manager
    original_get_running_loop = asyncio.get_running_loop
    asyncio.get_running_loop = lambda: type("Loop", (), {"time": lambda self: 100.0})()
    try:
        result = await monitor.check_health()
    finally:
        asyncio.get_running_loop = original_get_running_loop

    assert result.healthy is False
    assert result.error == "pong_stale"
    assert websocket.ping_calls == 0
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_websocket_exception_records_failure():
    websocket = DummyWebSocket(ping_exception=WebSocketException("boom"))
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 0
    monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS

    result = await monitor.check_health()

    assert result.healthy is False
    assert "boom" in (result.error or "")
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_oserror_records_failure():
    websocket = DummyWebSocket(ping_exception=OSError("network down"))
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 0
    monitor.pong_timeout_seconds = DEFAULT_WEBSOCKET_PONG_TIMEOUT_SECONDS

    result = await monitor.check_health()

    assert result.healthy is False
    assert "network down" in (result.error or "")
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_websocket_monitor_skips_ping_when_recent_and_reports_healthy():
    websocket = DummyWebSocket()
    monitor = WebSocketHealthMonitor("svc", DummyConnectionProvider(websocket))
    monitor.ping_interval_seconds = 10
    monitor.last_ping_time = 95.0
    monitor.last_pong_time = 95.0

    original_get_running_loop = asyncio.get_running_loop
    asyncio.get_running_loop = lambda: type("Loop", (), {"time": lambda self: 100.0})()
    try:
        result = await monitor.check_health()
    finally:
        asyncio.get_running_loop = original_get_running_loop

    assert result.healthy is True
    assert websocket.ping_calls == 0
