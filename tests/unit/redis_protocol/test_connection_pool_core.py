"""Tests for Redis connection pool core module."""

from __future__ import annotations

import asyncio
import threading
import time
import weakref
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis
import redis.asyncio
from redis.asyncio.retry import Retry as AsyncRetry
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry as SyncRetry

from common.redis_protocol import connection_pool_core


class TestRedisConnectionHealthMonitor:
    """Tests for RedisConnectionHealthMonitor class."""

    def test_initial_metrics(self) -> None:
        """Initial metrics are all zero."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        metrics = monitor.get_metrics()

        assert metrics["connections_created"] == 0
        assert metrics["connections_reused"] == 0
        assert metrics["connection_errors"] == 0
        assert metrics["pool_cleanups"] == 0
        assert metrics["pool_gets"] == 0
        assert metrics["pool_returns"] == 0
        assert metrics["connection_reuse_rate"] == 0

    def test_record_connection_created(self) -> None:
        """Record connection created increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_connection_created()

        metrics = monitor.get_metrics()
        assert metrics["connections_created"] == 1

    def test_record_connection_reused(self) -> None:
        """Record connection reused increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_connection_reused()

        metrics = monitor.get_metrics()
        assert metrics["connections_reused"] == 1

    def test_record_pool_get(self) -> None:
        """Record pool get increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_pool_get()

        metrics = monitor.get_metrics()
        assert metrics["pool_gets"] == 1

    def test_record_pool_return(self) -> None:
        """Record pool return increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_pool_return()

        metrics = monitor.get_metrics()
        assert metrics["pool_returns"] == 1

    def test_record_connection_error(self) -> None:
        """Record connection error increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_connection_error()

        metrics = monitor.get_metrics()
        assert metrics["connection_errors"] == 1

    def test_record_pool_cleanup(self) -> None:
        """Record pool cleanup increments counter."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        monitor.record_pool_cleanup()

        metrics = monitor.get_metrics()
        assert metrics["pool_cleanups"] == 1

    def test_reuse_rate_calculation(self) -> None:
        """Reuse rate is calculated correctly."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()

        # Simulate 10 pool gets with only 2 new connections created
        for _ in range(10):
            monitor.record_pool_get()
        monitor.record_connection_created()
        monitor.record_connection_created()

        metrics = monitor.get_metrics()
        # 10 gets - 2 created = 8 reuse operations out of 10 = 80%
        assert metrics["connection_reuse_rate"] == 0.8

    def test_should_perform_health_check_returns_true_after_interval(self) -> None:
        """Returns True when enough time has passed since last check."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()
        monitor.last_health_check = time.time() - 60  # 60 seconds ago

        assert monitor.should_perform_health_check() is True

    def test_should_perform_health_check_returns_false_before_interval(self) -> None:
        """Returns False when not enough time has passed."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()
        monitor.last_health_check = time.time()  # Just now

        assert monitor.should_perform_health_check() is False

    def test_thread_safety_of_metrics(self) -> None:
        """Metrics updates are thread-safe."""
        monitor = connection_pool_core.RedisConnectionHealthMonitor()
        iterations = 100

        def increment_metrics():
            for _ in range(iterations):
                monitor.record_pool_get()
                monitor.record_connection_created()

        threads = [threading.Thread(target=increment_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        metrics = monitor.get_metrics()
        assert metrics["pool_gets"] == 500
        assert metrics["connections_created"] == 500


class TestRetryCreation:
    """Tests for retry instance creation functions."""

    def test_create_async_retry_returns_retry_instance(self) -> None:
        """Creates async retry with correct type."""
        retry = connection_pool_core.create_async_retry()

        assert isinstance(retry, AsyncRetry)

    def test_create_sync_retry_returns_retry_instance(self) -> None:
        """Creates sync retry with correct type."""
        retry = connection_pool_core.create_sync_retry()

        assert isinstance(retry, SyncRetry)


class TestGetRedisPool:
    """Tests for get_redis_pool function."""

    @pytest.mark.asyncio
    async def test_get_redis_pool_creates_pool_when_none(self) -> None:
        """Creates pool when unified pool is None."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", None),
            patch.object(
                connection_pool_core,
                "_create_pool_if_needed",
                new_callable=AsyncMock,
            ) as mock_create,
            patch.object(
                connection_pool_core,
                "_should_recycle_pool",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
        ):
            # Simulate pool creation by setting _unified_pool after call
            async def set_pool(_loop):
                connection_pool_core._unified_pool = mock_pool

            mock_create.side_effect = set_pool

            result = await connection_pool_core.get_redis_pool()

            assert result is mock_pool
            mock_create.assert_awaited_once()
            mock_monitor.record_pool_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_pool_recycles_on_loop_change(self) -> None:
        """Cleans up pool when event loop changes."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(
                connection_pool_core,
                "_should_recycle_pool",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch.object(
                connection_pool_core,
                "cleanup_redis_pool",
                new_callable=AsyncMock,
            ) as mock_cleanup,
            patch.object(
                connection_pool_core,
                "_create_pool_if_needed",
                new_callable=AsyncMock,
            ),
            patch.object(connection_pool_core, "_redis_health_monitor"),
        ):
            await connection_pool_core.get_redis_pool()

            mock_cleanup.assert_awaited_once()


class TestShouldRecyclePool:
    """Tests for _should_recycle_pool function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_pool_loop_is_none(self) -> None:
        """Returns False when pool_loop is None."""
        current_loop = asyncio.get_event_loop()

        result = await connection_pool_core._should_recycle_pool(current_loop)

        # With _pool_loop as None (default), should not recycle
        with patch.object(connection_pool_core, "_pool_loop", None):
            result = await connection_pool_core._should_recycle_pool(current_loop)
            assert result is False


class TestGetRedisClient:
    """Tests for get_redis_client function."""

    @pytest.mark.asyncio
    async def test_get_redis_client_returns_client_with_pool(self) -> None:
        """Returns Redis client backed by connection pool."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.connection_kwargs = {"protocol": None}

        with patch.object(
            connection_pool_core,
            "get_redis_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ):
            client = await connection_pool_core.get_redis_client()

            assert isinstance(client, redis.asyncio.Redis)


class TestCleanupRedisPool:
    """Tests for cleanup_redis_pool function."""

    @pytest.mark.asyncio
    async def test_cleanup_when_pool_is_none(self) -> None:
        """Handles cleanup when pool is None."""
        with (
            patch.object(connection_pool_core, "_unified_pool", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool()

    @pytest.mark.asyncio
    async def test_cleanup_disconnects_pool(self) -> None:
        """Disconnects pool during cleanup."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.disconnect = AsyncMock()

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(connection_pool_core, "_pool_loop", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch.object(
                connection_pool_core,
                "_disconnect_pool",
                new_callable=AsyncMock,
            ) as mock_disconnect,
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
        ):
            await connection_pool_core.cleanup_redis_pool()

            mock_disconnect.assert_awaited_once()
            mock_monitor.record_pool_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_closed_event_loop(self) -> None:
        """Handles closed event loop during cleanup."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch(
                "asyncio.get_running_loop",
                side_effect=[MagicMock(is_closed=lambda: True)],
            ),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool()

    @pytest.mark.asyncio
    async def test_cleanup_handles_disconnect_timeout(self) -> None:
        """Handles timeout during pool disconnect."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(connection_pool_core, "_pool_loop", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch.object(
                connection_pool_core,
                "_disconnect_pool",
                new_callable=AsyncMock,
                side_effect=asyncio.TimeoutError(),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor"),
            patch.object(connection_pool_core, "logger"),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool()

    @pytest.mark.asyncio
    async def test_cleanup_handles_redis_error_during_disconnect(self) -> None:
        """Handles Redis error during disconnect."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(connection_pool_core, "_pool_loop", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch.object(
                connection_pool_core,
                "_disconnect_pool",
                new_callable=AsyncMock,
                side_effect=RedisError("Disconnect error"),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor"),
            patch.object(connection_pool_core, "logger"),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool()

    @pytest.mark.asyncio
    async def test_cleanup_handles_outer_redis_error(self) -> None:
        """Handles Redis error in outer try block."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)

        with (
            patch.object(connection_pool_core, "_unified_pool", mock_pool),
            patch.object(connection_pool_core, "_pool_loop", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch(
                "asyncio.get_running_loop",
                side_effect=RedisError("Outer error"),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
            patch.object(connection_pool_core, "logger"),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool()
            mock_monitor.record_connection_error.assert_called_once()


class TestDisconnectPool:
    """Tests for _disconnect_pool function."""

    @pytest.mark.asyncio
    async def test_disconnect_pool_in_current_loop(self) -> None:
        """Disconnects pool in current event loop."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.disconnect = AsyncMock()

        with patch.object(connection_pool_core, "_pool_loop", None):
            await connection_pool_core._disconnect_pool(mock_pool, timeout=5.0)

            mock_pool.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_pool_handles_event_loop_closed_error(self) -> None:
        """Handles event loop closed error during disconnect."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.disconnect = AsyncMock(side_effect=RuntimeError("Event loop is closed"))

        with patch.object(connection_pool_core, "_pool_loop", None):
            # Should not raise
            await connection_pool_core._disconnect_pool(mock_pool, timeout=5.0)

    @pytest.mark.asyncio
    async def test_disconnect_pool_reraises_other_runtime_errors(self) -> None:
        """Re-raises non-event-loop RuntimeErrors."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.disconnect = AsyncMock(side_effect=RuntimeError("Other error"))

        with (
            patch.object(connection_pool_core, "_pool_loop", None),
            pytest.raises(RuntimeError, match="Other error"),
        ):
            await connection_pool_core._disconnect_pool(mock_pool, timeout=5.0)

    @pytest.mark.asyncio
    async def test_disconnect_pool_with_different_loop(self) -> None:
        """Uses pool's original loop when different from current."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool.disconnect = AsyncMock()

        mock_other_loop = MagicMock()
        mock_other_loop.is_closed.return_value = False

        pool_loop_ref = MagicMock(return_value=mock_other_loop)

        with (
            patch.object(connection_pool_core, "_pool_loop", pool_loop_ref),
            patch("asyncio.run_coroutine_threadsafe") as mock_threadsafe,
            patch("asyncio.wrap_future", new_callable=AsyncMock) as mock_wrap,
            patch("asyncio.wait_for", new_callable=AsyncMock),
        ):
            mock_future = MagicMock()
            mock_threadsafe.return_value = mock_future

            await connection_pool_core._disconnect_pool(mock_pool, timeout=5.0)

            mock_threadsafe.assert_called_once()


class TestPerformRedisHealthCheck:
    """Tests for perform_redis_health_check function."""

    @pytest.mark.asyncio
    async def test_health_check_passes(self) -> None:
        """Returns True when health check passes."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_client = MagicMock()
        mock_client.ping = AsyncMock()
        mock_client.set = AsyncMock()
        mock_client.get = AsyncMock(return_value="test_value")
        mock_client.delete = AsyncMock()
        mock_client.aclose = AsyncMock()

        with (
            patch.object(
                connection_pool_core,
                "get_redis_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
            patch("redis.asyncio.Redis", return_value=mock_client),
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
        ):
            result = await connection_pool_core.perform_redis_health_check()

            assert result is True
            mock_monitor.record_pool_return.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_fails_on_value_mismatch(self) -> None:
        """Returns False when stored value doesn't match."""
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_client = MagicMock()
        mock_client.ping = AsyncMock()
        mock_client.set = AsyncMock()
        mock_client.get = AsyncMock(return_value="wrong_value")
        mock_client.delete = AsyncMock()
        mock_client.aclose = AsyncMock()

        with (
            patch.object(
                connection_pool_core,
                "get_redis_pool",
                new_callable=AsyncMock,
                return_value=mock_pool,
            ),
            patch("redis.asyncio.Redis", return_value=mock_client),
            patch.object(connection_pool_core, "_redis_health_monitor"),
            patch.object(connection_pool_core, "logger"),
        ):
            result = await connection_pool_core.perform_redis_health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_fails_on_redis_error(self) -> None:
        """Returns False when Redis error occurs."""
        with (
            patch.object(
                connection_pool_core,
                "get_redis_pool",
                new_callable=AsyncMock,
                side_effect=RedisConnectionError("Connection failed"),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
            patch.object(connection_pool_core, "logger"),
        ):
            result = await connection_pool_core.perform_redis_health_check()

            assert result is False
            mock_monitor.record_connection_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_fails_on_timeout(self) -> None:
        """Returns False when timeout occurs."""
        with (
            patch.object(
                connection_pool_core,
                "get_redis_pool",
                new_callable=AsyncMock,
                side_effect=RedisTimeoutError("Timeout"),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor,
            patch.object(connection_pool_core, "logger"),
        ):
            result = await connection_pool_core.perform_redis_health_check()

            assert result is False
            mock_monitor.record_connection_error.assert_called_once()


class TestGetRedisPoolMetrics:
    """Tests for get_redis_pool_metrics function."""

    def test_returns_metrics_from_health_monitor(self) -> None:
        """Returns metrics from the health monitor."""
        with patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor:
            mock_monitor.get_metrics.return_value = {"pool_gets": 10}

            result = connection_pool_core.get_redis_pool_metrics()

            assert result == {"pool_gets": 10}


class TestRecordPoolAcquiredAndReturned:
    """Tests for record_pool_acquired and record_pool_returned functions."""

    def test_record_pool_acquired(self) -> None:
        """Records pool acquisition."""
        with patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor:
            connection_pool_core.record_pool_acquired()

            mock_monitor.record_pool_get.assert_called_once()

    def test_record_pool_returned(self) -> None:
        """Records pool return."""
        with patch.object(connection_pool_core, "_redis_health_monitor") as mock_monitor:
            connection_pool_core.record_pool_returned()

            mock_monitor.record_pool_return.assert_called_once()


class TestCleanupRedisPoolOnNetworkIssues:
    """Tests for cleanup_redis_pool_on_network_issues function."""

    @pytest.mark.asyncio
    async def test_cleanup_on_network_issues(self) -> None:
        """Cleans up pool and resets references on network issues."""
        with (
            patch.object(
                connection_pool_core,
                "cleanup_redis_pool",
                new_callable=AsyncMock,
            ) as mock_cleanup,
            patch.object(connection_pool_core, "logger"),
        ):
            await connection_pool_core.cleanup_redis_pool_on_network_issues()

            mock_cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cleanup_on_network_issues_handles_error(self) -> None:
        """Handles error during network-triggered cleanup."""
        with (
            patch.object(
                connection_pool_core,
                "cleanup_redis_pool",
                new_callable=AsyncMock,
                side_effect=RedisError("Cleanup error"),
            ),
            patch.object(connection_pool_core, "logger"),
        ):
            # Should not raise
            await connection_pool_core.cleanup_redis_pool_on_network_issues()


class TestGetSyncRedisPool:
    """Tests for get_sync_redis_pool function."""

    def test_creates_sync_pool(self) -> None:
        """Creates synchronous connection pool."""
        with (
            patch.object(connection_pool_core, "_sync_pool", None),
            patch.object(connection_pool_core, "_sync_pool_guard", threading.Lock()),
            patch("redis.ConnectionPool") as mock_pool_class,
            patch.object(connection_pool_core, "config") as mock_config,
        ):
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_PASSWORD = None
            mock_config.REDIS_SSL = False

            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool

            result = connection_pool_core.get_sync_redis_pool()

            assert result is mock_pool
            mock_pool_class.assert_called_once()

    def test_reuses_existing_sync_pool(self) -> None:
        """Reuses existing synchronous pool."""
        mock_pool = MagicMock(spec=redis.ConnectionPool)

        with patch.object(connection_pool_core, "_sync_pool", mock_pool):
            result = connection_pool_core.get_sync_redis_pool()

            assert result is mock_pool

    def test_creates_sync_pool_with_password(self) -> None:
        """Creates pool with password when configured."""
        with (
            patch.object(connection_pool_core, "_sync_pool", None),
            patch.object(connection_pool_core, "_sync_pool_guard", threading.Lock()),
            patch("redis.ConnectionPool") as mock_pool_class,
            patch.object(connection_pool_core, "config") as mock_config,
        ):
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_PASSWORD = "secret"
            mock_config.REDIS_SSL = False

            connection_pool_core.get_sync_redis_pool()

            call_kwargs = mock_pool_class.call_args[1]
            assert call_kwargs["password"] == "secret"

    def test_creates_sync_pool_with_ssl(self) -> None:
        """Creates pool with SSL when configured."""
        with (
            patch.object(connection_pool_core, "_sync_pool", None),
            patch.object(connection_pool_core, "_sync_pool_guard", threading.Lock()),
            patch("redis.ConnectionPool") as mock_pool_class,
            patch.object(connection_pool_core, "config") as mock_config,
        ):
            mock_config.REDIS_HOST = "localhost"
            mock_config.REDIS_PORT = 6379
            mock_config.REDIS_DB = 0
            mock_config.REDIS_SOCKET_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_CONNECT_TIMEOUT = 5.0
            mock_config.REDIS_SOCKET_KEEPALIVE = True
            mock_config.REDIS_PASSWORD = None
            mock_config.REDIS_SSL = True

            connection_pool_core.get_sync_redis_pool()

            call_kwargs = mock_pool_class.call_args[1]
            assert call_kwargs["ssl"] is True


class TestGetSyncRedisClient:
    """Tests for get_sync_redis_client function."""

    def test_returns_client_with_sync_pool(self) -> None:
        """Returns synchronous Redis client backed by pool."""
        mock_pool = MagicMock(spec=redis.ConnectionPool)

        with (
            patch.object(
                connection_pool_core,
                "get_sync_redis_pool",
                return_value=mock_pool,
            ),
            patch("redis.Redis") as mock_redis_class,
        ):
            mock_client = MagicMock()
            mock_redis_class.return_value = mock_client

            result = connection_pool_core.get_sync_redis_client()

            assert result is mock_client
            mock_redis_class.assert_called_once()


class TestCreatePoolIfNeeded:
    """Tests for _create_pool_if_needed function."""

    @pytest.mark.asyncio
    async def test_creates_pool_when_unified_pool_is_none(self) -> None:
        """Creates pool when unified_pool is None."""
        current_loop = asyncio.get_event_loop()
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool_loop = weakref.ref(current_loop)

        with (
            patch.object(connection_pool_core, "_unified_pool", None),
            patch.object(connection_pool_core, "_pool_guard", threading.Lock()),
            patch.object(
                connection_pool_core,
                "_acquire_thread_lock",
                new_callable=AsyncMock,
            ),
            patch.object(
                connection_pool_core,
                "_initialize_pool_helper",
                new_callable=AsyncMock,
                return_value=(mock_pool, mock_pool_loop),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor"),
        ):
            await connection_pool_core._create_pool_if_needed(current_loop)


class TestInitializePool:
    """Tests for _initialize_pool function."""

    @pytest.mark.asyncio
    async def test_initializes_pool(self) -> None:
        """Initializes pool and sets module-level variables."""
        current_loop = asyncio.get_event_loop()
        mock_pool = MagicMock(spec=redis.asyncio.ConnectionPool)
        mock_pool_loop = weakref.ref(current_loop)

        with (
            patch.object(
                connection_pool_core,
                "_initialize_pool_helper",
                new_callable=AsyncMock,
                return_value=(mock_pool, mock_pool_loop),
            ),
            patch.object(connection_pool_core, "_redis_health_monitor"),
        ):
            await connection_pool_core._initialize_pool(current_loop)


class TestModuleConstants:
    """Tests for module-level constants and configuration."""

    def test_unified_redis_config_has_required_keys(self) -> None:
        """UNIFIED_REDIS_CONFIG has required configuration keys."""
        assert "max_connections" in connection_pool_core.UNIFIED_REDIS_CONFIG
        assert "dns_cache_ttl" in connection_pool_core.UNIFIED_REDIS_CONFIG
        assert "dns_cache_size" in connection_pool_core.UNIFIED_REDIS_CONFIG

    def test_retry_on_connection_error_has_expected_exceptions(self) -> None:
        """RETRY_ON_CONNECTION_ERROR contains expected exception types."""
        assert RedisConnectionError in connection_pool_core.RETRY_ON_CONNECTION_ERROR
        assert RedisTimeoutError in connection_pool_core.RETRY_ON_CONNECTION_ERROR
        # Check tuple has 2 or more exceptions for retry logic
        assert len(connection_pool_core.RETRY_ON_CONNECTION_ERROR) >= 2

    def test_redis_setup_errors_has_expected_exceptions(self) -> None:
        """REDIS_SETUP_ERRORS contains expected exception types."""
        assert RedisError in connection_pool_core.REDIS_SETUP_ERRORS
        # REDIS_SETUP_ERRORS should contain multiple exception types for error handling
        assert len(connection_pool_core.REDIS_SETUP_ERRORS) >= 5
