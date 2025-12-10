import asyncio
from types import SimpleNamespace

import aiohttp
import pytest

from common.connection_config import ConnectionConfig
from common.rest_connection_manager import RESTConnectionManager

_CONST_200 = 200
_CONST_503 = 503


class FakeConnector:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


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
    def __init__(self, responses=None):
        self._responses = responses or []
        self.closed = False
        self._connector = FakeConnector()
        self.last_request = None
        self.last_get = None

    def queue_response(self, response):
        self._responses.append(response)

    def _next(self):
        if self._responses:
            return self._responses.pop(0)
        return FakeResponse()

    def get(self, *args, **kwargs):
        self.last_get = (args, kwargs)
        return FakeRequestContext(self._next())

    def request(self, *args, **kwargs):
        self.last_request = (args, kwargs)
        return FakeRequestContext(self._next())

    async def close(self):
        self.closed = True


@pytest.fixture
def patched_environment(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(
        "common.rest_connection_manager.aiohttp.ClientSession",
        lambda *args, **kwargs: fake_session,
    )
    monkeypatch.setattr(
        "common.rest_connection_manager.track_existing_session",
        lambda session, name: "session-id",
    )
    closed_ids = []
    monkeypatch.setattr(
        "common.rest_connection_manager.track_session_close",
        lambda session_id: closed_ids.append(session_id),
    )
    monkeypatch.setattr(
        "common.connection_manager.get_connection_config",
        lambda service: ConnectionConfig(),
    )
    return fake_session, closed_ids


@pytest.mark.asyncio
async def test_establish_connection_and_make_requests(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))  # Health check

    manager = RESTConnectionManager(
        service_name="rest-test",
        base_url="https://example.com",
        alerter=SimpleNamespace(),
    )

    assert await manager.establish_connection()
    assert manager.is_connected()

    session.queue_response(FakeResponse(status=200, payload={"ok": True}))
    data = await manager.make_json_request("GET", "/health")
    assert data == {"ok": True}

    session.queue_response(FakeResponse(status=500, content_type="text/plain"))
    failure = await manager.make_json_request("GET", "/error")
    assert failure is None
    assert manager.consecutive_request_failures == 1

    await manager.cleanup_connection()
    assert not manager.session
    assert closed_ids == ["session-id"]


@pytest.mark.asyncio
async def test_establish_connection_health_check_failure_triggers_cleanup(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=503))

    manager = RESTConnectionManager(
        service_name="rest-test",
        base_url="https://example.com",
    )

    with pytest.raises(ConnectionError):
        await manager.establish_connection()

    assert manager.session is None
    assert session.closed is True
    assert closed_ids == ["session-id"]
    assert manager.consecutive_request_failures == 1


@pytest.mark.asyncio
async def test_make_request_with_authentication_handler(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    auth_calls = []

    def auth_handler(method, endpoint):
        auth_calls.append((method, endpoint))
        return {"Authorization": "Bearer token"}

    manager = RESTConnectionManager(
        service_name="rest-auth",
        base_url="https://example.com",
        authentication_handler=auth_handler,
    )

    assert await manager.establish_connection()
    assert auth_calls[0] == ("GET", "/health")

    session.queue_response(FakeResponse(status=200, payload={"ok": True}))
    response = await manager.make_request("POST", "/data")
    assert response.status == _CONST_200
    args, kwargs = session.last_request
    assert args[0] == "POST"
    assert kwargs["headers"]["Authorization"] == "Bearer token"
    assert auth_calls[-1] == ("POST", "/data")

    await manager.cleanup_connection()


@pytest.mark.asyncio
async def test_make_request_without_connection_returns_none(patched_environment):
    session, closed_ids = patched_environment
    manager = RESTConnectionManager(
        service_name="rest-no-conn",
        base_url="https://example.com",
    )

    result = await manager.make_request("GET", "/status")
    assert result is None


@pytest.mark.asyncio
async def test_make_request_uses_secondary_auth_handler(monkeypatch, patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    auth_calls = []

    def auth_handler(method, endpoint):
        auth_calls.append(("main", method, endpoint))
        raise TypeError("wrong signature")

    def auth_handler_no_args():
        auth_calls.append(("secondary", None, None))
        return {"Authorization": "Bearer secondary"}

    manager = RESTConnectionManager(
        service_name="rest-auth-secondary",
        base_url="https://example.com",
        authentication_handler=lambda *args: (
            auth_handler_no_args() if len(args) == 0 else auth_handler(*args)
        ),
    )

    assert await manager.establish_connection()

    session.queue_response(FakeResponse(status=200, payload={"ok": True}))
    response = await manager.make_request("GET", "/resource")
    assert response.status == _CONST_200
    assert ("main", "GET", "/resource") in auth_calls or ("secondary", None, None) in auth_calls
    await manager.cleanup_connection()


@pytest.mark.asyncio
async def test_make_request_preserves_existing_headers(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    auth_calls = []

    def auth_handler(method, endpoint):
        auth_calls.append((method, endpoint))
        return {"Authorization": "Bearer token"}

    manager = RESTConnectionManager(
        service_name="rest-existing-headers",
        base_url="https://example.com",
        authentication_handler=auth_handler,
    )

    assert await manager.establish_connection()

    session.queue_response(FakeResponse(status=503))
    headers = {"X-Test": "value"}
    response = await manager.make_request("POST", "/resource", headers=headers)
    assert response.status == _CONST_503
    assert manager.consecutive_request_failures == 1
    # Authentication handler should have been called only for health check
    assert auth_calls == [("GET", "/health")]
    await manager.cleanup_connection()


@pytest.mark.asyncio
async def test_make_request_handles_client_error(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    manager = RESTConnectionManager(
        service_name="rest-client-error",
        base_url="https://example.com",
    )

    assert await manager.establish_connection()

    session.queue_response(aiohttp.ClientError("boom"))
    result = await manager.make_request("GET", "/boom")
    assert result is None
    assert manager.consecutive_request_failures == 1

    await manager.cleanup_connection()


@pytest.mark.asyncio
async def test_check_connection_health_handles_timeout(patched_environment, monkeypatch):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    manager = RESTConnectionManager(
        service_name="rest-timeout",
        base_url="https://example.com",
    )

    assert await manager.establish_connection()

    session.queue_response(asyncio.TimeoutError())
    healthy = await manager.check_connection_health()
    assert healthy.healthy is False
    assert manager.consecutive_request_failures == 1

    await manager.cleanup_connection()


@pytest.mark.asyncio
async def test_get_connection_info_includes_rest_details(patched_environment):
    session, closed_ids = patched_environment
    session.queue_response(FakeResponse(status=200))

    manager = RESTConnectionManager(
        service_name="rest-info",
        base_url="https://example.com",
    )

    assert await manager.establish_connection()

    info = manager.get_connection_info()
    details = info["rest_details"]
    assert details["base_url"] == "https://example.com"
    assert details["health_check_endpoint"] == "/health"
    assert details["is_connected"] is True
    assert "connector_info" in details

    await manager.cleanup_connection()
