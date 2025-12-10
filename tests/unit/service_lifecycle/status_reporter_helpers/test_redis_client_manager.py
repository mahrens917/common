import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from common.service_lifecycle.status_reporter_helpers.redis_client_manager import (
    get_redis_client_for_reporter,
)


@pytest.mark.asyncio
async def test_returns_injected_client():
    injected = object()
    result = await get_redis_client_for_reporter(injected, None)
    assert result is injected


@pytest.mark.asyncio
async def test_returns_cached_client():
    cached = object()
    result = await get_redis_client_for_reporter(None, cached)
    assert result is cached


@pytest.mark.asyncio
async def test_creates_client_when_missing():
    mock_client = object()
    with patch(
        "common.redis_utils.get_redis_connection",
        AsyncMock(return_value=mock_client),
    ) as mocked:
        result = await get_redis_client_for_reporter(None, None)
        mocked.assert_awaited_once()
        assert result is mock_client
