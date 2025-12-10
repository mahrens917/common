from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.persistence_manager_helpers.connection_manager import (
    ConnectionManager,
)


@pytest.mark.asyncio
async def test_get_redis_initializes_and_pings():
    cm = ConnectionManager()
    fake_pool = object()
    fake_redis = MagicMock()
    fake_redis.ping = AsyncMock(return_value=True)

    with (
        patch(
            "common.redis_protocol.persistence_manager_helpers.connection_manager.get_redis_pool",
            AsyncMock(return_value=fake_pool),
        ),
        patch(
            "common.redis_protocol.persistence_manager_helpers.connection_manager.Redis",
            MagicMock(return_value=fake_redis),
        ),
    ):
        redis = await cm.get_redis()

    assert redis is fake_redis
    assert cm.redis is fake_redis
    assert cm._initialized is True
    fake_redis.ping.assert_awaited()


@pytest.mark.asyncio
async def test_get_redis_retries_after_ping_failure():
    cm = ConnectionManager()
    failing = MagicMock()
    failing.ping = AsyncMock(side_effect=asyncio.TimeoutError())
    recovered = MagicMock()
    recovered.ping = AsyncMock(return_value=True)

    cm.redis = failing
    cm._initialized = True

    async def ensure_conn_success():
        cm.redis = recovered
        cm._initialized = True
        return True

    cm.ensure_connection = AsyncMock(side_effect=ensure_conn_success)

    redis = await cm.get_redis()

    assert redis is recovered


@pytest.mark.asyncio
async def test_ensure_connection_handles_redis_errors():
    cm = ConnectionManager()

    with patch(
        "common.redis_protocol.persistence_manager_helpers.connection_manager.get_redis_pool",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        ok = await cm.ensure_connection()

    assert ok is False
    assert cm.redis is None


@pytest.mark.asyncio
async def test_close_handles_errors_and_resets_state():
    cm = ConnectionManager()
    fake_redis = MagicMock()
    fake_redis.aclose = AsyncMock(side_effect=RuntimeError("fail"))
    cm.redis = fake_redis
    cm._initialized = True
    cm._pool = object()

    await cm.close()

    assert cm.redis is None
    assert cm._initialized is False
