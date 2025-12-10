"""
Redis connection management for price history tracking

Handles connection lifecycle (initialization, cleanup, validation) for
PriceHistoryTracker with event loop conflict prevention.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from common.redis_connection_manager import RedisConnectionManager
from common.redis_protocol.error_types import REDIS_ERRORS
from common.redis_protocol.typing import RedisClient


class PriceHistoryConnectionManager(RedisConnectionManager):
    """
    Manages Redis connection lifecycle for price history tracking.

    Inherits common Redis safety logic while keeping tracker-specific error messaging.
    """

    def __init__(self, connection_factory: Optional[Callable[[], Awaitable[RedisClient]]] = None):
        super().__init__(
            connection_factory,
            not_initialized_message="Redis client not initialized for PriceHistoryTracker",
        )


__all__ = ["PriceHistoryConnectionManager", "REDIS_ERRORS"]
