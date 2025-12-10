"""Tests for the shared Redis connection manager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_connection_manager import RedisConnectionManager


@pytest.mark.asyncio
async def test_initialize_sets_client(monkeypatch):
    connection = MagicMock()
    factory = AsyncMock(return_value=connection)
    manager = RedisConnectionManager(connection_factory=factory)

    await manager.initialize()
    assert manager.redis_client is connection
    factory.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_closes_existing_connection(monkeypatch):
    first_client = MagicMock()
    first_client.aclose = AsyncMock()

    new_client = MagicMock()
    factory = AsyncMock(return_value=new_client)
    manager = RedisConnectionManager(connection_factory=factory)
    manager.redis_client = first_client

    await manager.initialize()
    first_client.aclose.assert_awaited_once()
    assert manager.redis_client is new_client


@pytest.mark.asyncio
async def test_initialize_propagates_errors(monkeypatch):
    factory = AsyncMock(side_effect=RuntimeError("boom"))
    manager = RedisConnectionManager(connection_factory=factory)

    with pytest.raises(RuntimeError):
        await manager.initialize()


@pytest.mark.asyncio
async def test_cleanup_handles_close_errors():
    client = MagicMock()
    client.aclose = AsyncMock(side_effect=RuntimeError("fail"))
    manager = RedisConnectionManager(connection_factory=AsyncMock())
    manager.redis_client = client

    await manager.cleanup()
    assert manager.redis_client is None


def test_get_client_raises_when_uninitialized():
    manager = RedisConnectionManager(connection_factory=AsyncMock())

    with pytest.raises(ConnectionError, match="Redis client not initialized"):
        manager.get_client()
