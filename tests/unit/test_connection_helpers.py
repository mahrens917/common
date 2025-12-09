import asyncio

import pytest

from src.common.connection_helpers import ensure_session_or_raise, ensure_websocket_or_raise
from src.common.health.types import HealthCheckResult


class DummyLogger:
    def __init__(self):
        self.messages = []

    def error(self, message: str) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_ensure_session_or_raise_accepts_health_result():
    logger = DummyLogger()

    async def healthy():
        return HealthCheckResult(True)

    await ensure_session_or_raise(healthy, operation="fetch", logger=logger)
    assert logger.messages == []


@pytest.mark.asyncio
async def test_ensure_session_or_raise_raises_on_failure():
    logger = DummyLogger()

    async def unhealthy():
        return HealthCheckResult(False, error="not ready")

    with pytest.raises(RuntimeError):
        await ensure_session_or_raise(unhealthy, operation="fetch", logger=logger)

    assert any("not ready" in message for message in logger.messages)


@pytest.mark.asyncio
async def test_ensure_websocket_or_raise_interprets_boolean_checks():
    logger = DummyLogger()

    async def healthy():
        return True

    await ensure_websocket_or_raise(healthy, operation="listen", logger=logger)

    async def unhealthy():
        return False

    with pytest.raises(RuntimeError):
        await ensure_websocket_or_raise(unhealthy, operation="listen", logger=logger)
