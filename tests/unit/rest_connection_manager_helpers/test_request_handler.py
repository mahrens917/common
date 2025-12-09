"""Tests for the rest connection manager request handler stub."""

import pytest

from src.common.rest_connection_manager_helpers.request_handler import RequestHandler


class DummyHandler(RequestHandler):
    async def handle_request(self, *args, **kwargs):
        return "handled"


def test_request_handler_sets_kwargs():
    handler = DummyHandler(extra="value")
    assert handler.extra == "value"
    assert hasattr(handler, "_shutdown_requested")


@pytest.mark.asyncio
async def test_request_handler_raises_if_not_implemented():
    base = RequestHandler()

    with pytest.raises(NotImplementedError):
        await base.handle_request()


def test_shutdown_request_mixin_sets_flag():
    handler = DummyHandler()
    handler._shutdown_requested = False
    handler.request_shutdown()
    assert handler._shutdown_requested
