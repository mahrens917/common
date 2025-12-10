"""Tests for the ReconnectionHandler stub."""

import pytest

from common.connection_manager_helpers.reconnection_handler import ReconnectionHandler


class TestReconnectionHandler:
    def test_init_stores_kwargs_and_defaults_flag(self) -> None:
        handler = ReconnectionHandler(source="test", retries=1)

        assert handler.source == "test"
        assert handler.retries == 1
        assert handler._shutdown_requested is False

    def test_request_shutdown_marks_flag(self) -> None:
        handler = ReconnectionHandler()

        handler.request_shutdown()

        assert handler._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_reconnect_stub_raises(self) -> None:
        handler = ReconnectionHandler()

        with pytest.raises(NotImplementedError):
            await handler.reconnect()
