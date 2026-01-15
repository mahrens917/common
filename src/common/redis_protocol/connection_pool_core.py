"""
Redis connection management with unified connection pooling
"""

from __future__ import annotations

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
from .connection_pool_helpers.connection_management import initialize_pool as _initialize_pool_helper
from .connection_pool_helpers.retry_config import RETRY_ON_CONNECTION_ERROR, create_async_retry, create_sync_retry

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

# Thread-local storage for Redis connection pools
# Each thread gets its own pool tied to its own event loop
_thread_local = threading.local()

# Synchronous Redis connection pool (for rare sync operations)
# This remains global since sync operations don't have event loop issues
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
    Get thread-local Redis connection pool for all operations.

    Each thread gets its own pool tied to its event loop, avoiding
    cross-thread cleanup issues that cause connection timeouts.

    Returns:
        Redis connection pool for the current thread
    """
    current_loop = asyncio.get_running_loop()

    # Get thread-local pool state
    pool: Optional[redis.asyncio.ConnectionPool] = getattr(_thread_local, "pool", None)
    pool_loop_ref: Optional[weakref.ReferenceType] = getattr(_thread_local, "pool_loop", None)

    # Check if this thread's pool needs recycling (rare: same thread, different loop)
    if pool is not None and pool_loop_ref is not None:
        pool_loop = pool_loop_ref()
        if pool_loop is None or pool_loop is not current_loop:
            await _cleanup_thread_local_pool()
            pool = None

    # Create pool for this thread if needed
    if pool is None:
        pool = await _create_thread_local_pool(current_loop)

    _redis_health_monitor.record_pool_get()
    return pool


async def _create_thread_local_pool(
    current_loop: asyncio.AbstractEventLoop,
) -> redis.asyncio.ConnectionPool:
    """Create a new pool for the current thread."""
    pool, pool_loop = await _initialize_pool_helper(current_loop, UNIFIED_REDIS_CONFIG, _redis_health_monitor)
    _thread_local.pool = pool
    _thread_local.pool_loop = pool_loop
    logger.info("Created thread-local Redis pool for thread %s", threading.current_thread().name)
    return pool


async def _cleanup_thread_local_pool() -> None:
    """Clean up the current thread's pool (same-thread, safe operation)."""
    pool: Optional[redis.asyncio.ConnectionPool] = getattr(_thread_local, "pool", None)
    if pool is not None:
        try:
            await asyncio.wait_for(pool.disconnect(), timeout=5.0)
            logger.info("Cleaned up thread-local Redis pool")
        except asyncio.TimeoutError:  # Transient network/connection failure  # policy_guard: allow-silent-handler
            logger.debug("Pool cleanup timed out, state reset")
        except REDIS_SETUP_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.debug("Pool cleanup error (%s), state reset", type(exc).__name__)
        _thread_local.pool = None
        _thread_local.pool_loop = None
        _redis_health_monitor.record_pool_cleanup()


async def get_redis_client() -> redis.asyncio.Redis:
    """Get a Redis client backed by the unified async connection pool.

    The client is configured with automatic retry on connection drops
    using exponential backoff.
    """
    pool = await get_redis_pool()
    return redis.asyncio.Redis(
        connection_pool=pool,
        retry=create_async_retry(),
        retry_on_error=list(RETRY_ON_CONNECTION_ERROR),
    )


async def cleanup_redis_pool():
    """Clean up the current thread's Redis connection pool.

    With thread-local pools, this only affects the calling thread's pool.
    No cross-thread cleanup is needed, avoiding timeout issues.
    """
    await _cleanup_thread_local_pool()


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

    except REDIS_SETUP_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
        logger.debug("Health check failed (%s)", type(exc).__name__)
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
    """Clean up current thread's Redis pool during network issues."""
    try:
        logger.info("Cleaning up thread-local Redis pool due to network issues")
        await cleanup_redis_pool()
        logger.info("Thread-local Redis pool cleanup completed")
    except REDIS_SETUP_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
        logger.debug("Network cleanup error (%s), pool reset", type(exc).__name__)


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

    The client is configured with automatic retry on connection drops
    using exponential backoff.

    Returns:
        Synchronous Redis client from connection pool

    Example:
        >>> client = get_sync_redis_client()
        >>> client.set("key", "value")
        >>> value = client.get("key")
        >>> client.close()  # Return connection to pool
    """
    pool = get_sync_redis_pool()
    return redis.Redis(
        connection_pool=pool,
        retry=create_sync_retry(),
        retry_on_error=list(RETRY_ON_CONNECTION_ERROR),
    )
