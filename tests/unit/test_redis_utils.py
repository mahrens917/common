from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common import redis_utils
from common.redis_utils import RedisOperationError


@pytest.mark.asyncio
async def test_get_redis_connection_uses_pool(monkeypatch):
    pool_sentinel = object()
    fresh_client = AsyncMock()

    async def fake_get_pool():
        return pool_sentinel

    def fake_async_redis(*, connection_pool, **kwargs):
        assert connection_pool is pool_sentinel
        return fresh_client

    monkeypatch.setattr("common.redis_protocol.connection_pool_core.get_redis_pool", fake_get_pool)
    monkeypatch.setattr(redis_utils.redis.asyncio, "Redis", fake_async_redis)

    client = await redis_utils.get_redis_connection()

    assert client is fresh_client


@pytest.mark.asyncio
async def test_get_redis_connection_raises_on_pool_error(monkeypatch):
    async def fake_get_pool():
        raise RuntimeError("pool down")

    monkeypatch.setattr("common.redis_protocol.connection_pool_core.get_redis_pool", fake_get_pool)

    with pytest.raises(ConnectionError) as excinfo:
        await redis_utils.get_redis_connection()

    assert "pool down" in str(excinfo.value)


@pytest.mark.asyncio
async def test_ensure_keyspace_notifications_adds_missing_flags(monkeypatch):
    redis_client = AsyncMock()
    redis_client.config_get.return_value = {"notify-keyspace-events": "K"}

    await redis_utils.ensure_keyspace_notifications(redis_client, required_flags="Kh")

    redis_client.config_set.assert_awaited_once_with("notify-keyspace-events", "Kh")


@pytest.mark.asyncio
async def test_ensure_keyspace_notifications_skips_when_flags_present():
    redis_client = AsyncMock()
    redis_client.config_get.return_value = {"notify-keyspace-events": b"Kh"}

    await redis_utils.ensure_keyspace_notifications(redis_client, required_flags="Kh")

    redis_client.config_set.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_keyspace_notifications_no_flags():
    redis_client = AsyncMock()

    await redis_utils.ensure_keyspace_notifications(redis_client, required_flags="")

    redis_client.config_get.assert_not_awaited()
    redis_client.config_set.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_redis_connection_closes_supplied_client():
    redis_client = AsyncMock()

    await redis_utils.cleanup_redis_connection(redis_client)

    redis_client.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_cleanup_redis_connection_raises_when_close_fails():
    redis_client = AsyncMock()
    redis_client.aclose.side_effect = RuntimeError("boom")

    with pytest.raises(redis_utils.RedisOperationError) as excinfo:
        await redis_utils.cleanup_redis_connection(redis_client)

    redis_client.aclose.assert_awaited_once_with()
    assert "Redis close failed" in str(excinfo.value)


def test_redis_operation_error_includes_details():
    err = RedisOperationError("read", details="key missing")
    assert "key missing" in str(err)


@pytest.mark.asyncio
async def test_cleanup_redis_connection_no_aclose():
    redis_client = MagicMock(spec=[])  # no aclose attribute
    # Should return without error
    await redis_utils.cleanup_redis_connection(redis_client)


@pytest.mark.asyncio
async def test_ensure_keyspace_notifications_empty_current():
    redis_client = AsyncMock()
    redis_client.config_get.return_value = {"notify-keyspace-events": ""}

    await redis_utils.ensure_keyspace_notifications(redis_client, required_flags="Kh")

    redis_client.config_set.assert_awaited_once_with("notify-keyspace-events", "Kh")


@pytest.mark.asyncio
async def test_get_pubsub_redis_connection_success(monkeypatch):
    fake_client = AsyncMock()
    fake_class = MagicMock(return_value=fake_client)

    fake_config = MagicMock()
    fake_config.REDIS_HOST = "localhost"
    fake_config.REDIS_PORT = 6379
    fake_config.REDIS_DB = 0
    fake_config.REDIS_SOCKET_CONNECT_TIMEOUT = 5
    fake_config.REDIS_SOCKET_KEEPALIVE = True
    fake_config.REDIS_PASSWORD = None
    fake_config.REDIS_SSL = False

    monkeypatch.setattr("common.redis_protocol.config", fake_config)
    monkeypatch.setattr(redis_utils.redis.asyncio, "Redis", fake_class)

    client = await redis_utils.get_pubsub_redis_connection()
    assert client is fake_client
    fake_client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_pubsub_redis_connection_raises_on_ping_failure(monkeypatch):
    fake_client = AsyncMock()
    fake_client.ping.side_effect = ConnectionError("no redis")
    fake_class = MagicMock(return_value=fake_client)

    fake_config = MagicMock()
    fake_config.REDIS_HOST = "localhost"
    fake_config.REDIS_PORT = 6379
    fake_config.REDIS_DB = 0
    fake_config.REDIS_SOCKET_CONNECT_TIMEOUT = 5
    fake_config.REDIS_SOCKET_KEEPALIVE = True
    fake_config.REDIS_PASSWORD = None
    fake_config.REDIS_SSL = False

    monkeypatch.setattr("common.redis_protocol.config", fake_config)
    monkeypatch.setattr(redis_utils.redis.asyncio, "Redis", fake_class)

    with pytest.raises(ConnectionError):
        await redis_utils.get_pubsub_redis_connection()
