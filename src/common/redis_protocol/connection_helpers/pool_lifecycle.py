"""
Redis pool lifecycle validation and cleanup.

Why: Separates pool lifecycle concerns from main pool acquisition logic
How: Validates event loop state and handles pool cleanup on loop changes
"""

import asyncio
import logging
import weakref
from typing import Optional

import redis.asyncio

logger = logging.getLogger(__name__)


async def should_rebuild_pool(
    pool: Optional[redis.asyncio.ConnectionPool],
    pool_loop: Optional[weakref.ReferenceType[asyncio.AbstractEventLoop]],
    current_loop: asyncio.AbstractEventLoop,
) -> bool:
    """
    Check if pool needs to be rebuilt due to event loop changes.

    Args:
        pool: Current connection pool
        pool_loop: Weak reference to pool's event loop
        current_loop: Currently running event loop

    Returns:
        True if pool should be rebuilt, False otherwise
    """
    if pool is None:
        _none_guard_value = False
        return _none_guard_value

    if pool_loop is None:
        _none_guard_value = False
        return _none_guard_value

    cached_loop = pool_loop()
    if cached_loop is None:
        _none_guard_value = True
        return _none_guard_value

    if cached_loop.is_closed():
        return True

    if cached_loop is not current_loop:
        return True

    return False
