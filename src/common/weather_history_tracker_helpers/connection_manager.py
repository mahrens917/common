"""Redis connection lifecycle management for weather history tracking"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from src.common.redis_connection_manager import RedisConnectionManager
from src.common.redis_protocol.typing import RedisClient


class WeatherHistoryConnectionManager(RedisConnectionManager):
    """Manages Redis connection lifecycle for weather history operations."""

    def __init__(self, connection_factory: Optional[Callable[[], Awaitable[RedisClient]]] = None):
        super().__init__(
            connection_factory,
            not_initialized_message="Redis client not initialized for WeatherHistoryTracker",
        )
