"""Tests for REST health monitor behaviors."""

import asyncio
from unittest.mock import MagicMock

import aiohttp
import pytest

from common.health.types import HealthCheckResult
from common.rest_connection_manager_helpers.health_monitor import RESTHealthMonitor


class DummyResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


class DummySession:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception

    def get(self, *args, **kwargs):
        if self.exception:
            raise self.exception
        return DummyResponse(self.response)


class DummySessionManager:
    def __init__(self, session=None):
        self.session = session

    def get_session(self):
        return self.session


def make_monitor(**overrides):
    session_manager = overrides.get("session_manager", DummySessionManager())
    auth_handler = overrides.get("auth_handler")
    monitor = RESTHealthMonitor(
        "testservice",
        "http://base",
        "/health",
        session_manager,
        auth_handler,
    )
    return monitor


@pytest.mark.asyncio
async def test_check_health_fails_when_session_closed():
    monitor = make_monitor(session_manager=DummySessionManager(None))

    result = await monitor.check_health()

    assert result == HealthCheckResult(False, error="session_closed")
    assert monitor.consecutive_failures == 1


@pytest.mark.asyncio
async def test_check_health_success(monkeypatch):
    session = DummySession(response=200)
    monitor = make_monitor(session_manager=DummySessionManager(session))

    result = await monitor.check_health()

    assert result.healthy
    assert monitor.consecutive_failures == 0


@pytest.mark.asyncio
async def test_check_health_failure_status(monkeypatch):
    session = DummySession(response=500)
    monitor = make_monitor(session_manager=DummySessionManager(session))

    result = await monitor.check_health()

    assert not result.healthy
    assert result.error == "HTTP 500"


@pytest.mark.asyncio
async def test_check_health_timeout(monkeypatch):
    session = MagicMock()
    session.get = MagicMock(side_effect=asyncio.TimeoutError())
    monitor = make_monitor(session_manager=DummySessionManager(session))

    result = await monitor.check_health()

    assert result == HealthCheckResult(False, error="timeout")


@pytest.mark.asyncio
async def test_check_health_client_error(monkeypatch):
    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp.ClientError("boom"))
    monitor = make_monitor(session_manager=DummySessionManager(session))

    result = await monitor.check_health()

    assert result.error == "boom"
