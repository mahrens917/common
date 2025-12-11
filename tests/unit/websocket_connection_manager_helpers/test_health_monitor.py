import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from websockets import WebSocketException

from common.health.types import HealthCheckResult
from common.websocket_connection_manager_helpers.health_monitor import WebSocketHealthMonitor


class TestWebSocketHealthMonitor:
    @pytest.fixture
    def connection_provider(self):
        provider = Mock()
        provider.get_connection = Mock()
        return provider

    @pytest.fixture
    def health_monitor(self, connection_provider):
        monitor = WebSocketHealthMonitor("test_service", connection_provider)
        # Mock BaseHealthMonitor methods (they are on the instance for the test's purpose)
        monitor.record_success = Mock()
        monitor.record_failure = Mock()
        return monitor

    @pytest.fixture
    def mock_websocket(self):
        ws = AsyncMock()
        ws.close_code = None

        def _instant_future(*_args, **_kwargs):
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            future.set_result(None)
            return future

        ws.ping = AsyncMock(side_effect=_instant_future)
        return ws

    def test_init(self, health_monitor):
        assert health_monitor.service_name == "test_service"
        assert health_monitor.ping_interval_seconds == 30

    def test_validate_websocket_connection_valid(self, health_monitor, mock_websocket):
        valid, error = health_monitor._validate_websocket_connection(mock_websocket)
        assert valid is True
        assert error is None

    def test_validate_websocket_connection_none(self, health_monitor):
        valid, error = health_monitor._validate_websocket_connection(None)
        assert valid is False
        assert error == "connection_missing"

    def test_validate_websocket_connection_closed(self, health_monitor, mock_websocket):
        mock_websocket.close_code = 1000
        valid, error = health_monitor._validate_websocket_connection(mock_websocket)
        assert valid is False
        assert error == "connection_closed"

    @pytest.mark.asyncio
    async def test_perform_ping_check_ping_interval_not_elapsed(self, health_monitor, mock_websocket):
        # Mock asyncio.get_running_loop().time() to control time
        with patch("asyncio.get_running_loop") as mock_loop:
            # We need to simulate time properly. Use a simple sequence of times.
            # Initial current_time for this test iteration.
            current_mock_time = 100.0 + 10  # A little bit after last_ping_time
            mock_loop.return_value.time.return_value = current_mock_time

            health_monitor.last_ping_time = 100.0  # Set last ping to an earlier time
            health_monitor.last_pong_time = 100.0  # Set last pong to an earlier time

            # current_time is just a little bit later, not enough to trigger new ping
            healthy, error = await health_monitor._perform_ping_check(mock_websocket, current_mock_time)
            assert healthy is True
            assert error is None
            mock_websocket.ping.assert_not_called()

    @pytest.mark.asyncio
    async def test_perform_ping_check_success(self, health_monitor, mock_websocket):
        # Mock asyncio.get_running_loop().time() to control time
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 100.0  # Consistent time for mocking

            current_time = 100.0 + health_monitor.ping_interval_seconds + 1  # Time to trigger ping
            health_monitor.last_ping_time = 100.0  # Initial last ping time
            health_monitor.last_pong_time = 100.0  # Initial last pong time

            healthy, error = await health_monitor._perform_ping_check(mock_websocket, current_time)

            assert healthy is True
            assert error is None
            mock_websocket.ping.assert_called_once()
            assert health_monitor.last_ping_time == current_time
            assert health_monitor.last_pong_time == current_time

    @pytest.mark.asyncio
    async def test_perform_ping_check_pong_timeout(self, health_monitor, mock_websocket):
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 100.0  # Consistent time for mocking
            current_time = 100.0 + health_monitor.ping_interval_seconds + 1  # Time to trigger ping

            health_monitor.last_ping_time = 100.0
            health_monitor.last_pong_time = 100.0

            # Mock the future returned by ping to never complete
            mock_pong_waiter = asyncio.Future()
            # Don't set result, so it will timeout
            mock_websocket.ping.return_value = mock_pong_waiter

            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                healthy, error = await health_monitor._perform_ping_check(mock_websocket, current_time)

                assert healthy is False
                assert error == "pong_timeout"

    @pytest.mark.asyncio
    async def test_perform_ping_check_pong_stale(self, health_monitor, mock_websocket):
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 100.0  # Consistent time for mocking
            current_time = 100.0 + health_monitor.ping_interval_seconds / 2  # Current time after ping interval, but not triggered new ping

            health_monitor.last_ping_time = 100.0  # Pinged recently
            health_monitor.last_pong_time = 100.0 - (health_monitor.ping_interval_seconds * 2 + 1)  # Pong is stale

            healthy, error = await health_monitor._perform_ping_check(mock_websocket, current_time)

            assert healthy is False
            assert error == "pong_stale"

    @pytest.mark.asyncio
    async def test_check_health_success(self, health_monitor, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket
        health_monitor._perform_ping_check = AsyncMock(return_value=(True, None))

        result = await health_monitor.check_health()

        assert result.healthy is True
        assert result.error is None
        health_monitor.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_connection_missing(self, health_monitor, connection_provider):
        connection_provider.get_connection.return_value = None

        result = await health_monitor.check_health()

        assert result.healthy is False
        assert result.error == "connection_missing"
        health_monitor.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_ping_check_failure(self, health_monitor, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket
        health_monitor._perform_ping_check = AsyncMock(return_value=(False, "pong_timeout"))

        result = await health_monitor.check_health()

        assert result.healthy is False
        assert result.error == "pong_timeout"
        health_monitor.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_websocket_exception(self, health_monitor, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket
        health_monitor._perform_ping_check = AsyncMock(side_effect=WebSocketException("WS Error"))

        result = await health_monitor.check_health()

        assert result.healthy is False
        assert "WS Error" in result.error
        health_monitor.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_unexpected_exception(self, health_monitor, connection_provider, mock_websocket):
        connection_provider.get_connection.return_value = mock_websocket
        health_monitor._perform_ping_check = AsyncMock(side_effect=RuntimeError("Unexpected"))

        result = await health_monitor.check_health()

        assert result.healthy is False
        assert "Unexpected" in result.error
        health_monitor.record_failure.assert_called_once()

    def test_initialize_pong_time(self, health_monitor):
        # Mock asyncio.get_running_loop().time()
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 100.0
            health_monitor.initialize_pong_time()
            assert health_monitor.last_ping_time == 0.0
            assert health_monitor.last_pong_time == 100.0
