import pytest

from common.rest_connection_manager_helpers.request_handler import RequestHandler


@pytest.mark.asyncio
async def test_request_handler_handle_request_noop():
    handler = RequestHandler()

    assert await handler.handle_request() is None


def test_request_handler_retains_dependencies():
    handler = RequestHandler(helper="value")

    assert handler.helper == "value"
