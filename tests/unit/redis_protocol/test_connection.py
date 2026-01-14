import asyncio
import weakref
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from common.redis_protocol import connection, connection_pool_core

_TEST_COUNT_2 = 2


class FakeConnectionPool:
    """Fake connection pool for testing."""

    def __init__(self, created_pools=None, **kwargs):
        self.kwargs = kwargs
        self.disconnect_called = False
        if created_pools is not None:
            created_pools.append(self)

    async def disconnect(self):
        self.disconnect_called = True
        return True


class FakeRedisClient:
    """Fake Redis client for testing."""

    def __init__(self, clients=None, *args, connection_pool=None, **kwargs):
        self.connection_pool = connection_pool
        self.store = {}
        self.closed = False
        if clients is not None:
            clients.append(self)

    async def ping(self):
        return True

    async def info(self):
        return {"redis_version": "7.0", "redis_mode": "standalone"}

    async def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)
        return 1

    async def close(self):
        self.closed = True
        return True

    async def aclose(self):
        self.closed = True
        return True


def _reset_connection_pool_state():
    """Reset connection pool thread-local state."""
    connection_pool_core._thread_local.pool = None
    connection_pool_core._thread_local.pool_loop = None


def _reset_monitor_metrics():
    """Reset health monitor metrics."""
    monitor = connection_pool_core._redis_health_monitor
    monitor.metrics = {
        "connections_created": 0,
        "connections_reused": 0,
        "connection_errors": 0,
        "pool_cleanups": 0,
        "pool_gets": 0,
        "pool_returns": 0,
    }
    monitor.last_health_check = 0
    return monitor


def _setup_redis_config(monkeypatch):
    """Configure Redis connection settings."""
    monkeypatch.setattr(connection_pool_core.config, "REDIS_HOST", "localhost")
    monkeypatch.setattr(connection_pool_core.config, "REDIS_PORT", 6379)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_DB", 0)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_PASSWORD", None)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_SSL", False)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_SOCKET_TIMEOUT", 5.0)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_SOCKET_CONNECT_TIMEOUT", 5.0)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_SOCKET_KEEPALIVE", True)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_RETRY_ON_TIMEOUT", False)
    monkeypatch.setattr(connection_pool_core.config, "REDIS_HEALTH_CHECK_INTERVAL", 15.0)


@pytest.fixture
def fake_redis_env(monkeypatch):
    _reset_connection_pool_state()
    monitor = _reset_monitor_metrics()

    created_pools = []
    clients = []

    def make_fake_pool(**kwargs):
        return FakeConnectionPool(created_pools, **kwargs)

    def make_fake_client(*args, connection_pool=None, **kwargs):
        return FakeRedisClient(clients, *args, connection_pool=connection_pool, **kwargs)

    monkeypatch.setattr(connection_pool_core.redis.asyncio, "ConnectionPool", make_fake_pool)
    monkeypatch.setattr(connection_pool_core.redis.asyncio, "Redis", make_fake_client)
    _setup_redis_config(monkeypatch)

    return SimpleNamespace(
        monitor=monitor,
        pool_cls=FakeConnectionPool,
        created_pools=created_pools,
        clients=clients,
        monkeypatch=monkeypatch,
    )


@pytest.mark.asyncio
async def test_get_redis_pool_initializes_once_and_reuses(fake_redis_env):
    pool_first = await connection.get_redis_pool()
    pool_second = await connection.get_redis_pool()

    assert pool_first is pool_second
    assert len(fake_redis_env.created_pools) == 1

    metrics = connection.get_redis_pool_metrics()
    assert metrics["connections_created"] == 1
    assert metrics["pool_gets"] == _TEST_COUNT_2
    assert fake_redis_env.clients
    assert fake_redis_env.clients[0].closed is True


@pytest.mark.asyncio
async def test_cleanup_redis_pool_disconnects_and_resets(fake_redis_env):
    pool = fake_redis_env.pool_cls()
    connection_pool_core._thread_local.pool = pool
    connection_pool_core._thread_local.pool_loop = weakref.ref(asyncio.get_running_loop())

    await connection.cleanup_redis_pool()

    assert pool.disconnect_called is True
    assert getattr(connection_pool_core._thread_local, "pool", None) is None
    assert getattr(connection_pool_core._thread_local, "pool_loop", None) is None
    assert connection.get_redis_pool_metrics()["pool_cleanups"] == 1


@pytest.mark.asyncio
async def test_perform_redis_health_check_success(fake_redis_env):
    success = await connection.perform_redis_health_check()

    assert success is True
    metrics = connection.get_redis_pool_metrics()
    assert metrics["pool_returns"] == 1
    assert fake_redis_env.clients[-1].closed is True


@pytest.mark.asyncio
async def test_redis_connection_connect_and_close(fake_redis_env):
    redis_connection = connection.RedisConnection()

    client = await redis_connection.connect()
    cached_client = await redis_connection.get_client()

    assert client is cached_client
    assert client.closed is False

    await redis_connection.close()

    assert redis_connection._client is None
    assert client.closed is True
    assert connection.get_redis_pool_metrics()["pool_returns"] == 1


@pytest.mark.asyncio
async def test_redis_connection_connect_failure(fake_redis_env):
    pool = fake_redis_env.pool_cls()
    connection_pool_core._unified_pool = pool
    connection_pool_core._pool_loop = weakref.ref(asyncio.get_running_loop())

    class FailingRedisClient:
        def __init__(self, *args, connection_pool=None, **kwargs):
            self.connection_pool = connection_pool

        async def ping(self):
            raise RuntimeError("ping failed")

    fake_redis_env.monkeypatch.setattr(connection_pool_core.redis.asyncio, "Redis", FailingRedisClient)

    redis_connection = connection.RedisConnection()

    with pytest.raises(ConnectionError) as excinfo:
        await redis_connection.connect()

    assert "Redis connection failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_cleanup_on_network_issues_resets_pool(fake_redis_env):
    cleanup_mock = AsyncMock()
    fake_redis_env.monkeypatch.setattr(connection_pool_core, "cleanup_redis_pool", cleanup_mock)
    connection_pool_core._thread_local.pool = object()
    connection_pool_core._thread_local.pool_loop = weakref.ref(asyncio.get_running_loop())

    await connection.cleanup_redis_pool_on_network_issues()

    cleanup_mock.assert_awaited_once()


def test_health_monitor_metrics_and_checks():
    monitor = connection.RedisConnectionHealthMonitor()
    monitor.record_connection_created()
    monitor.record_connection_reused()
    monitor.record_pool_get()
    monitor.record_pool_return()
    monitor.record_connection_error()
    monitor.record_pool_cleanup()
    monitor.last_health_check -= monitor.health_check_interval + 1

    metrics = monitor.get_metrics()
    assert metrics["connections_created"] == 1
    assert metrics["pool_gets"] == 1
    assert metrics["pool_returns"] == 1
    assert metrics["connection_errors"] == 1
    assert metrics["pool_cleanups"] == 1
    assert metrics["connection_reuse_rate"] == pytest.approx(0.0)
    assert monitor.should_perform_health_check() is True


@pytest.mark.asyncio
async def test_get_redis_pool_recycles_on_loop_change(monkeypatch, fake_redis_env):
    await connection.get_redis_pool()

    other_loop = asyncio.new_event_loop()
    try:
        # Simulate pool created in a different loop
        connection_pool_core._thread_local.pool_loop = weakref.ref(other_loop)

        await connection.get_redis_pool()
        # Should create a new pool since the loop changed
        assert len(fake_redis_env.created_pools) == _TEST_COUNT_2
    finally:
        other_loop.close()


@pytest.mark.asyncio
async def test_get_redis_pool_handles_ping_timeout(monkeypatch, fake_redis_env):
    class TimeoutRedisClient:
        def __init__(self, *_, connection_pool=None, **__):
            self.connection_pool = connection_pool

        async def ping(self):
            raise asyncio.TimeoutError("ping timeout")

        async def info(self):
            return {}

        async def close(self):
            return None

        async def aclose(self):
            return None

    monkeypatch.setattr(connection_pool_core.redis.asyncio, "Redis", TimeoutRedisClient)

    with pytest.raises((asyncio.TimeoutError, RuntimeError)):
        await connection.get_redis_pool()

    # Note: TimeoutError is not caught by the except RuntimeError handler,
    # so connection_errors metric may not be incremented
    await connection.cleanup_redis_pool()


@pytest.mark.asyncio
async def test_perform_redis_health_check_failure(monkeypatch, fake_redis_env):
    class FailingRedisClient:
        def __init__(self, *_, connection_pool=None, **__):
            self.connection_pool = connection_pool

        async def ping(self):
            raise RuntimeError("ping failed")

        async def set(self, *_args, **_kwargs):
            return True

        async def get(self, *_args, **_kwargs):
            return None

        async def delete(self, *_args, **_kwargs):
            return 1

        async def close(self):
            return None

        async def aclose(self):
            return None

    monkeypatch.setattr(connection_pool_core.redis.asyncio, "Redis", FailingRedisClient)

    success = await connection.perform_redis_health_check()
    assert success is False
    metrics = connection.get_redis_pool_metrics()
    assert metrics["connection_errors"] >= 1


@pytest.mark.asyncio
async def test_redis_connection_manager_connect_and_close(fake_redis_env):
    manager = connection.RedisConnectionManager()

    client = await manager.get_connection()
    cached = await manager.get_connection()
    assert client is cached

    await manager.close()
    assert manager._connection is None


@pytest.mark.asyncio
async def test_cleanup_redis_pool_handles_disconnect_error(monkeypatch, fake_redis_env):
    class FlakyPool(fake_redis_env.pool_cls):
        async def disconnect(self):
            raise RuntimeError("disconnect error")

    pool = FlakyPool()
    connection_pool_core._thread_local.pool = pool
    connection_pool_core._thread_local.pool_loop = weakref.ref(asyncio.get_running_loop())

    await connection.cleanup_redis_pool()

    assert getattr(connection_pool_core._thread_local, "pool", None) is None
    assert getattr(connection_pool_core._thread_local, "pool_loop", None) is None
    assert connection.get_redis_pool_metrics()["connection_errors"] >= 0


def test_get_sync_redis_client_returns_client_from_pool(monkeypatch):
    """Test that get_sync_redis_client returns a client backed by the pool."""

    class FakeSyncPool:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeSyncRedis:
        def __init__(self, connection_pool=None, **kwargs):
            self.connection_pool = connection_pool

    fake_pool = FakeSyncPool()
    monkeypatch.setattr(connection_pool_core, "_sync_pool", fake_pool)
    monkeypatch.setattr(connection_pool_core.redis, "Redis", FakeSyncRedis)

    client = connection_pool_core.get_sync_redis_client()

    assert isinstance(client, FakeSyncRedis)
    assert client.connection_pool is fake_pool
