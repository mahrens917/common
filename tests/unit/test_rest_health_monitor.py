import asyncio

import pytest

from common.health.types import HealthCheckResult
from common.rest_connection_manager_helpers.health_monitor import RESTHealthMonitor


class DummyResponse:
    def __init__(self, status: int):
        self.status = status


class DummyRequestContext:
    def __init__(self, response):
        self._response = response

    def __await__(self):
        async def _inner():
            if isinstance(self._response, Exception):
                raise self._response
            return self._response

        return _inner().__await__()

    async def __aenter__(self):
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


class DummySession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.closed = False

    def get(self, *args, **kwargs):
        return DummyRequestContext(self._responses.pop(0))


class DummySessionManager:
    def __init__(self, session: DummySession):
        self._session = session

    def get_session(self):
        return self._session


@pytest.mark.asyncio
async def test_rest_health_monitor_success_records_success():
    session = DummySession([DummyResponse(200)])
    monitor = RESTHealthMonitor(
        "test", "https://example.com", "/health", DummySessionManager(session), None
    )

    result = await monitor.check_health()

    assert result == HealthCheckResult(True, details={"status": 200}, error=None)
    assert monitor.consecutive_failures == 0
    assert monitor.last_success_time > 0


@pytest.mark.asyncio
async def test_rest_health_monitor_http_failure_increments_counter():
    session = DummySession([DummyResponse(503)])
    monitor = RESTHealthMonitor(
        "test", "https://example.com", "/health", DummySessionManager(session), None
    )

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.details == {"status": 503}
    assert result.error == "HTTP 503"
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_rest_health_monitor_timeout_records_failure():
    session = DummySession([asyncio.TimeoutError()])
    monitor = RESTHealthMonitor(
        "test", "https://example.com", "/health", DummySessionManager(session), None
    )

    result = await monitor.check_health()

    assert result.healthy is False
    assert result.error == "timeout"
    assert monitor.consecutive_failures == 1
