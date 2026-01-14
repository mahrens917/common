"""Connection pool creation and management logic."""

from __future__ import annotations

import asyncio
import logging
import weakref
from typing import Any

import redis.asyncio

from .. import config

logger = logging.getLogger(__name__)


async def initialize_pool(
    current_loop: asyncio.AbstractEventLoop, unified_redis_config: dict, health_monitor: Any
) -> tuple[redis.asyncio.ConnectionPool, weakref.ReferenceType]:
    """
    Initialize a Redis connection pool for the current thread.

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
