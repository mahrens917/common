"""
Redis connection management with unified connection pooling
"""

import asyncio
import logging
import threading
import time
import weakref
from typing import Any, Dict, Optional

import redis
import redis.asyncio
from redis.exceptions import RedisError

from . import config
from .connection_pool_helpers.connection_management import acquire_thread_lock as _acquire_thread_lock
from .connection_pool_helpers.connection_management import create_pool_if_needed as _create_pool_helper
from .connection_pool_helpers.connection_management import initialize_pool as _initialize_pool_helper
from .connection_pool_helpers.connection_management import should_recycle_pool as _should_recycle_pool_helper

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Only show WARNING and above

REDIS_SETUP_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
    RuntimeError,
    ValueError,
)

# Single unified connection pool for all Redis operations
_unified_pool: Optional[redis.asyncio.ConnectionPool] = None
_pool_guard = threading.Lock()  # Thread-aware guard for cross-loop safety
_pool_loop: Optional[weakref.ReferenceType[asyncio.AbstractEventLoop]] = None

# Synchronous Redis connection pool (for rare sync operations)
_sync_pool: Optional[redis.ConnectionPool] = None
_sync_pool_guard = threading.Lock()

# Unified connection pooling configuration
UNIFIED_REDIS_CONFIG = {
    "max_connections": 120,  # Optimized for 95%+ pool reuse rate
    "dns_cache_ttl": 300,  # 5 minutes
    "dns_cache_size": 1000,
}


# Connection pool health monitoring with reuse tracking
class RedisConnectionHealthMonitor:
    """Monitor Redis connection pool health and performance"""

    def __init__(self):
        self.metrics = {
            "connections_created": 0,
            "connections_reused": 0,
            "connection_errors": 0,
            "pool_cleanups": 0,
            "pool_gets": 0,  # Track pool connection requests
            "pool_returns": 0,  # Track pool connection returns
        }
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds
        self._lock = threading.Lock()  # Thread-safe metrics updates

    def record_connection_created(self):
        """Record a new connection creation"""
        with self._lock:
            self.metrics["connections_created"] += 1

    def record_connection_reused(self):
        """Record connection reuse"""
        with self._lock:
            self.metrics["connections_reused"] += 1

    def record_pool_get(self):
        """Record a connection request from pool"""
        with self._lock:
            self.metrics["pool_gets"] += 1

    def record_pool_return(self):
        """Record a connection return to pool"""
        with self._lock:
            self.metrics["pool_returns"] += 1

    def record_connection_error(self):
        """Record connection error"""
        with self._lock:
            self.metrics["connection_errors"] += 1

    def record_pool_cleanup(self):
        """Record pool cleanup event"""
        with self._lock:
            self.metrics["pool_cleanups"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self._lock:
            total_operations = self.metrics["pool_gets"]
            reuse_operations = max(0, self.metrics["pool_gets"] - self.metrics["connections_created"])

            return {
                **self.metrics,
                "last_health_check": self.last_health_check,
                "connection_reuse_rate": reuse_operations / max(total_operations, 1),
            }

    def should_perform_health_check(self) -> bool:
        """Check if health check should be performed"""
        return time.time() - self.last_health_check > self.health_check_interval


_redis_health_monitor = RedisConnectionHealthMonitor()


async def get_redis_pool() -> redis.asyncio.ConnectionPool:
    """
    Get unified Redis connection pool for all operations

    Returns:
        Redis connection pool
    """
    global _unified_pool, _pool_loop

    current_loop = asyncio.get_running_loop()

    # Check if pool needs rebuilding due to event loop changes
    if await _should_recycle_pool(current_loop):
        await cleanup_redis_pool()

    # Create pool if needed (with double-checked locking)
    if _unified_pool is None:
        await _create_pool_if_needed(current_loop)

    # Record pool access for reuse tracking
    _redis_health_monitor.record_pool_get()
    assert _unified_pool is not None
    return _unified_pool


async def _should_recycle_pool(current_loop: asyncio.AbstractEventLoop) -> bool:
    """
    Determine if the existing pool was created by a different event loop.
    """
    return await _should_recycle_pool_helper(_pool_loop, current_loop)


async def _create_pool_if_needed(current_loop: asyncio.AbstractEventLoop) -> None:
    """
    Create Redis pool if it doesn't exist (with thread-safe double-check).

    Args:
        current_loop: Currently running event loop
    """
    global _unified_pool, _pool_loop

    pool, pool_loop = await _create_pool_helper(
        _unified_pool,
        _pool_guard,
        _acquire_thread_lock,
        current_loop,
        UNIFIED_REDIS_CONFIG,
        _redis_health_monitor,
    )
    if pool is not None:
        _unified_pool = pool
        _pool_loop = pool_loop


async def _initialize_pool(current_loop: asyncio.AbstractEventLoop) -> None:
    """
    Initialize the unified Redis connection pool.
    """
    global _unified_pool, _pool_loop

    pool, pool_loop = await _initialize_pool_helper(current_loop, UNIFIED_REDIS_CONFIG, _redis_health_monitor)
    _unified_pool = pool
    _pool_loop = pool_loop


async def get_redis_client() -> redis.asyncio.Redis:
    """Get a Redis client backed by the unified async connection pool."""
    pool = await get_redis_pool()
    return redis.asyncio.Redis(connection_pool=pool)


async def cleanup_redis_pool():
    """Clean up unified Redis connection pool"""
    global _unified_pool, _pool_loop

    await _acquire_thread_lock(_pool_guard)
    try:
        if _unified_pool is not None:
            try:
                # Check if event loop is still running before attempting cleanup
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_closed():
                        logger.warning("Event loop is closed, skipping Redis pool cleanup")
                        _unified_pool = None
                        return
                except RuntimeError:  # policy_guard: allow-silent-handler
                    # No running loop, safe to proceed
                    pass

                # Attempt graceful disconnect with timeout
                try:
                    await _disconnect_pool(_unified_pool, timeout=5.0)
                    logger.info("Cleaned up unified Redis connection pool")
                except asyncio.TimeoutError:  # policy_guard: allow-silent-handler
                    logger.warning("Redis pool cleanup timed out after 5 seconds")
                except REDIS_SETUP_ERRORS as disconnect_error:  # policy_guard: allow-silent-handler
                    logger.exception(
                        "Error during Redis pool disconnect (%s)",
                        type(disconnect_error).__name__,
                    )
                    # Continue with cleanup despite disconnect error

                _unified_pool = None
                _redis_health_monitor.record_pool_cleanup()
                _pool_loop = None

            except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
                # Don't raise on cleanup errors during teardown, but log them
                logger.exception(
                    "Error during Redis pool cleanup (%s)",
                    type(exc).__name__,
                )
                _redis_health_monitor.record_connection_error()
                _unified_pool = None  # Still clear the pool reference to prevent memory leaks
    finally:
        if _pool_guard.locked():
            _pool_guard.release()


async def _disconnect_pool(pool: redis.asyncio.ConnectionPool, *, timeout: float) -> None:
    """Disconnect pool cleanly, favoring the loop that created it."""

    pool_loop = _pool_loop() if _pool_loop else None
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:  # policy_guard: allow-silent-handler
        current_loop = None

    if pool_loop and pool_loop is not current_loop and not pool_loop.is_closed():
        try:
            future = asyncio.run_coroutine_threadsafe(pool.disconnect(), pool_loop)
            await asyncio.wait_for(asyncio.wrap_future(future), timeout=timeout)
        except (RuntimeError, asyncio.CancelledError):  # policy_guard: allow-silent-handler
            pass
        else:
            return

    await asyncio.wait_for(pool.disconnect(), timeout=timeout)


async def perform_redis_health_check() -> bool:
    """
    Perform Redis connection health check

    Returns:
        True if health check passes, False otherwise
    """
    try:
        pool = await get_redis_pool()
        test_client = redis.asyncio.Redis(connection_pool=pool)

        # Perform basic connectivity test
        await test_client.ping()

        # Test basic operations
        test_key = "health_check_test"
        await test_client.set(test_key, "test_value", ex=10)  # 10 second expiry
        value = await test_client.get(test_key)
        await test_client.delete(test_key)

        await test_client.aclose()
        _redis_health_monitor.record_pool_return()  # Track connection return

        success = value == "test_value"

        if success:
            logger.debug("Redis health check passed")
        else:
            logger.warning("Redis health check failed - value mismatch")

    except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
        logger.exception(
            "Redis health check failed (%s)",
            type(exc).__name__,
        )
        _redis_health_monitor.record_connection_error()
        return False
    else:
        return success


def get_redis_pool_metrics() -> Dict[str, Any]:
    """Get Redis connection pool metrics"""
    return _redis_health_monitor.get_metrics()


def record_pool_acquired() -> None:
    """Record that a pool connection was acquired."""
    _redis_health_monitor.record_pool_get()


def record_pool_returned() -> None:
    """Record that a pool connection was returned."""
    _redis_health_monitor.record_pool_return()


async def cleanup_redis_pool_on_network_issues():
    """Clean up Redis connection pool during network issues"""
    try:
        logger.info("Cleaning up Redis connection pool due to network issues")
        await cleanup_redis_pool()

        # Force recreation of pool on next access
        global _unified_pool, _pool_loop
        _unified_pool = None
        _pool_loop = None

        logger.info("Redis connection pool cleanup completed")

    except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
        logger.exception(
            "Error during network-triggered Redis pool cleanup (%s)",
            type(exc).__name__,
        )


def get_sync_redis_pool() -> redis.ConnectionPool:
    """
    Get synchronous Redis connection pool for rare sync operations.

    Note: Most code should use the async pool (get_redis_pool). This sync pool
    is only for special cases where async operations are not possible (e.g.,
    synchronous persistence in PDF pipeline).

    Returns:
        Synchronous Redis connection pool
    """
    global _sync_pool

    with _sync_pool_guard:
        if _sync_pool is None:
            pool_kwargs = {
                "host": config.REDIS_HOST,
                "port": config.REDIS_PORT,
                "db": config.REDIS_DB,
                "max_connections": 20,  # Lower limit for rare sync operations
                "socket_timeout": config.REDIS_SOCKET_TIMEOUT,
                "socket_connect_timeout": config.REDIS_SOCKET_CONNECT_TIMEOUT,
                "socket_keepalive": config.REDIS_SOCKET_KEEPALIVE,
                "decode_responses": True,  # Ensure responses are decoded to strings
            }
            if config.REDIS_PASSWORD:
                pool_kwargs["password"] = config.REDIS_PASSWORD
            if config.REDIS_SSL:
                pool_kwargs["ssl"] = True

            _sync_pool = redis.ConnectionPool(**pool_kwargs)
            logger.info("Created synchronous Redis connection pool (max_connections=20)")

        return _sync_pool


def get_sync_redis_client() -> redis.Redis:
    """
    Get synchronous Redis client backed by connection pool.

    Note: Most code should use async clients (get_redis_client). This is only for
    special cases where async operations are not possible.

    Returns:
        Synchronous Redis client from connection pool

    Example:
        >>> client = get_sync_redis_client()
        >>> client.set("key", "value")
        >>> value = client.get("key")
        >>> client.close()  # Return connection to pool
    """
    pool = get_sync_redis_pool()
    return redis.Redis(connection_pool=pool)
