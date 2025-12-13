"""Connection pool creation and management logic."""

import asyncio
import logging
import threading
import weakref
from typing import Any, Callable, Optional

import redis.asyncio

from .. import config

logger = logging.getLogger(__name__)


async def acquire_thread_lock(lock: threading.Lock) -> None:
    """Asynchronously acquire a threading.Lock without blocking the event loop."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lock.acquire)


async def should_recycle_pool(
    pool_loop: Optional[weakref.ReferenceType[asyncio.AbstractEventLoop]],
    current_loop: asyncio.AbstractEventLoop,
) -> bool:
    """
    Determine if the existing pool was created by a different event loop.
    """
    if pool_loop is None:
        _none_guard_value = False
        return _none_guard_value
    previous_loop = pool_loop()
    if previous_loop is None:
        _none_guard_value = False
        return _none_guard_value
    if previous_loop is current_loop:
        return False
    logger.info("Detected event loop change; recycling unified Redis connection pool")
    return True


async def initialize_pool(
    current_loop: asyncio.AbstractEventLoop, unified_redis_config: dict, health_monitor: Any
) -> tuple[redis.asyncio.ConnectionPool, weakref.ReferenceType]:
    """
    Initialize the unified Redis connection pool.

    Returns:
        Tuple of (pool, pool_loop_weakref)
    """
    try:
        pool_kwargs = {
            "host": config.REDIS_HOST,
            "port": config.REDIS_PORT,
            "db": config.REDIS_DB,
            "max_connections": unified_redis_config["max_connections"],
            "socket_timeout": config.REDIS_SOCKET_TIMEOUT,
            "socket_connect_timeout": config.REDIS_SOCKET_CONNECT_TIMEOUT,
            "retry_on_timeout": config.REDIS_RETRY_ON_TIMEOUT,
            "socket_keepalive": config.REDIS_SOCKET_KEEPALIVE,
        }
        if config.REDIS_PASSWORD:
            pool_kwargs["password"] = config.REDIS_PASSWORD
        if getattr(config, "REDIS_HEALTH_CHECK_INTERVAL", None):
            pool_kwargs["health_check_interval"] = config.REDIS_HEALTH_CHECK_INTERVAL
        if config.REDIS_SSL:
            pool_kwargs["ssl"] = True

        # All downstream consumers expect decoded ``str`` responses rather than
        # ``bytes`` (atomic operations, PDF loaders, etc.). Ensure the unified
        # pool enables ``decode_responses`` so every client inherits that setting.
        pool_kwargs["decode_responses"] = True

        pool = redis.asyncio.ConnectionPool(**pool_kwargs)
        client = redis.asyncio.Redis(connection_pool=pool)
        await client.ping()
        await client.aclose()
    except RuntimeError:
        health_monitor.record_connection_error()
        raise
    else:
        pool_loop = weakref.ref(current_loop)
        health_monitor.record_connection_created()
        return pool, pool_loop


async def create_pool_if_needed(
    unified_pool: Any,
    pool_guard: Any,
    acquire_thread_lock: Callable[[Any], Any],
    current_loop: asyncio.AbstractEventLoop,
    unified_redis_config: dict,
    health_monitor: Any,
) -> tuple[Any, Any]:
    """
    Create Redis pool if it doesn't exist (with thread-safe double-check).

    Args:
        unified_pool: Current pool instance or None
        pool_guard: Thread lock for pool access
        acquire_thread_lock: Function to acquire lock asynchronously
        current_loop: Currently running event loop
        unified_redis_config: Configuration dict
        health_monitor: Health monitor instance

    Returns:
        Tuple of (pool, pool_loop_weakref)
    """
    await acquire_thread_lock(pool_guard)
    try:
        # Double-check after acquiring lock
        if unified_pool is not None:
            return None, None

        pool, pool_loop = await initialize_pool(current_loop, unified_redis_config, health_monitor)
        return pool, pool_loop
    finally:
        if pool_guard.locked():
            pool_guard.release()
