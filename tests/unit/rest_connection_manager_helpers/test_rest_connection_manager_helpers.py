import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest

from common.rest_connection_manager_helpers.connection_lifecycle import RESTConnectionLifecycle
from common.rest_connection_manager_helpers.health_monitor import RESTHealthMonitor
from common.rest_connection_manager_helpers.request_operations import RESTRequestOperations
from common.rest_connection_manager_helpers.session_manager import RESTSessionManager

pytestmark = pytest.mark.unit


class DummyHealthResult:
    def __init__(self, healthy: bool, details=None):
        self.healthy = healthy
        self.details = details or {}


class StubSessionManager:
    def __init__(self):
        self.created = False
        self.closed = False

    async def create_session(self):
        self.created = True

    async def close_session(self):
        self.closed = True


class StubHealthMonitor:
    def __init__(self, healthy=True):
        self.healthy = healthy
        self.checked = 0

    async def check_health(self):
        self.checked += 1
        return DummyHealthResult(self.healthy)


@pytest.mark.asyncio
async def test_connection_lifecycle_establish_and_cleanup(monkeypatch):
    session_manager = StubSessionManager()
    health_monitor = StubHealthMonitor(healthy=True)
    lifecycle = RESTConnectionLifecycle("svc", "http://example.com", session_manager, health_monitor)

    assert await lifecycle.establish_connection() is True
    assert session_manager.created is True
    assert health_monitor.checked == 1

    await lifecycle.cleanup_connection()
    assert session_manager.closed is True

    # Health failure should trigger cleanup and raise
    lifecycle = RESTConnectionLifecycle("svc", "http://example.com", session_manager, StubHealthMonitor(healthy=False))
    with pytest.raises(ConnectionError):
        await lifecycle.establish_connection()
    assert session_manager.closed is True


@pytest.mark.asyncio
async def test_connection_lifecycle_handles_client_error(monkeypatch):
    session_manager = StubSessionManager()
    health_monitor = StubHealthMonitor(healthy=True)
    lifecycle = RESTConnectionLifecycle("svc", "http://example.com", session_manager, health_monitor)

    async def failing_create():
        raise aiohttp.ClientError("boom")

    monkeypatch.setattr(session_manager, "create_session", failing_create)

    with pytest.raises(ConnectionError):
        await lifecycle.establish_connection()
    assert session_manager.closed is True


class FakeResponse:
    def __init__(self, status=200, content_type="application/json", payload=None):
        self.status = status
        self.content_type = content_type
        self._payload = payload or {}

    async def json(self):
        return self._payload

    def __await__(self):
        async def _inner():
            return self

        return _inner().__await__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


class FakeRequestContext:
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


class FakeSession:
    def __init__(self):
        self.requests = []
        self.closed = False

    def request(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        return FakeRequestContext(kwargs.pop("_response"))


class StubHealthRecorder:
    def __init__(self):
        self.successes = 0
        self.failures = 0
        self.request_failures = 0

    def record_success(self):
        self.successes += 1

    def record_failure(self):
        self.failures += 1

    def record_request_failure(self):
        self.request_failures += 1


@pytest.mark.asyncio
async def test_request_operations_make_request_and_json(monkeypatch):
    session = FakeSession()
    session_manager = SimpleNamespace(get_session=lambda: session)
    health_monitor = StubHealthRecorder()

    operations = RESTRequestOperations(
        "svc",
        "http://example.com",
        session_manager,
        auth_handler=lambda: {"Auth": "token"},
        health_monitor=health_monitor,
    )

    response = FakeResponse(status=201, payload={"ok": True})
    result = await operations.make_request("GET", "/health", _response=response)
    assert result.status == 201
    assert health_monitor.successes == 1

    json_result = await operations.make_json_request("POST", "/data", _response=FakeResponse(payload={"value": 1}))
    assert json_result == {"value": 1}

    bad_content = await operations.make_json_request("GET", "/plain", _response=FakeResponse(content_type="text/plain", status=200))
    assert bad_content is None
    assert health_monitor.request_failures == 1


@pytest.mark.asyncio
async def test_request_operations_handles_errors(monkeypatch):
    session = FakeSession()
    session_manager = SimpleNamespace(get_session=lambda: session)
    health_monitor = StubHealthRecorder()
    operations = RESTRequestOperations(
        "svc",
        "http://example.com",
        session_manager,
        auth_handler=None,
        health_monitor=health_monitor,
    )

    session.request = AsyncMock(side_effect=aiohttp.ClientError("boom"))
    assert await operations.make_request("GET", "/err") is None
    assert health_monitor.failures == 1

    session.request = AsyncMock(side_effect=asyncio.TimeoutError())
    assert await operations.make_request("GET", "/timeout") is None
    assert health_monitor.failures == 2

    # No session available
    operations.session_manager = SimpleNamespace(get_session=lambda: None)
    assert await operations.make_request("GET", "/no-session") is None


class FakeConnector:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeClientSession:
    def __init__(self, *args, **kwargs):
        self.closed = False
        self._connector = FakeConnector()

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_rest_session_manager_lifecycle(monkeypatch):
    created = []
    closed = []
    monkeypatch.setattr(
        "common.rest_connection_manager_helpers.session_manager.aiohttp.ClientSession",
        lambda *args, **kwargs: FakeClientSession(),
    )
    monkeypatch.setattr(
        "common.rest_connection_manager_helpers.session_manager.aiohttp.TCPConnector",
        lambda *args, **kwargs: FakeConnector(),
    )

    manager = RESTSessionManager(
        "svc",
        connection_timeout=1.0,
        request_timeout=2.0,
        track_creation=lambda session, name: (created.append(name), "sid")[1],
        track_close=lambda sid: closed.append(sid),
    )

    session = await manager.create_session()
    assert manager.session is session
    assert created == ["svc_rest_manager"]

    await manager.close_session()
    assert closed == ["sid"]
    assert manager.session is None

    # Closing with no active session should be a no-op
    await manager.close_session()
