"""
Redis pool initialization coordinator.

Why: Coordinates pool creation, testing, and logging
How: Encapsulates the full pool initialization sequence
"""

import asyncio
import logging
import weakref

import redis
import redis.asyncio

from .pool_settings import build_pool_settings, mask_sensitive_settings
from .pool_validator import test_pool_connection

logger = logging.getLogger(__name__)


async def create_and_test_pool(
    max_connections: int,
    host: str,
    port: int,
    db: int,
    current_loop: asyncio.AbstractEventLoop,
) -> tuple[redis.asyncio.ConnectionPool, weakref.ReferenceType[asyncio.AbstractEventLoop]]:
    """
    Create Redis connection pool and validate it works.

    Args:
        max_connections: Maximum connections for pool
        host: Redis host
        port: Redis port
        db: Redis database number
        current_loop: Current event loop

    Returns:
        Tuple of (created pool, weak reference to current loop)

    Raises:
        RuntimeError: If pool creation or testing fails
    """
    logger.info(f"Redis package version: {redis.__version__}")
    logger.info("Creating unified Redis connection pool with settings:")

    pool_settings = build_pool_settings(max_connections)
    masked_settings = mask_sensitive_settings(pool_settings)
    logger.info(f"Unified pool settings: {masked_settings}")

    pool = redis.asyncio.ConnectionPool(**pool_settings)
    logger.info(f"Created unified pool: {pool}, type: {type(pool)}")

    await test_pool_connection(pool, host, port, db)

    logger.info(f"Initialized unified Redis connection pool: " f"host={host} port={port} max_connections={max_connections}")

    pool_loop = weakref.ref(current_loop)
    return pool, pool_loop
