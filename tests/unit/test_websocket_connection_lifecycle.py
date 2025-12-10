from unittest.mock import AsyncMock

import pytest

from common.websocket_connection_manager_helpers.connection_lifecycle import (
    WebSocketConnectionLifecycle,
    _validate_connection,
)


@pytest.mark.asyncio
async def test_establish_connection_wraps_transport_error_and_cleans_up():
    async def failing_factory():
        raise OSError("dns failure")

    lifecycle = WebSocketConnectionLifecycle(
        "svc",
        "ws://example.test",
        connection_timeout=0.1,
        connection_factory=failing_factory,
    )
    lifecycle.cleanup_connection = AsyncMock()

    with pytest.raises(ConnectionError) as excinfo:
        await lifecycle.establish_connection()

    assert "Transport error" in str(excinfo.value)
    lifecycle.cleanup_connection.assert_awaited_once()


def test_validate_connection_none_marks_error_as_cleaned():
    with pytest.raises(ConnectionError) as excinfo:
        _validate_connection(None, "svc")

    error = excinfo.value
    assert getattr(error, "_already_cleaned") is True


def test_validate_connection_closed_marks_error_as_cleaned():
    class DummyConnection:
        close_code = 4400

    with pytest.raises(ConnectionError) as excinfo:
        _validate_connection(DummyConnection(), "svc")

    error = excinfo.value
    assert getattr(error, "_already_cleaned") is True
