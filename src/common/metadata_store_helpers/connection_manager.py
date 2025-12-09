"""Redis connection management for MetadataStore"""

import logging
from typing import Optional

from src.common.redis_protocol.typing import RedisClient
from src.common.redis_utils import get_redis_connection

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages Redis connection lifecycle for MetadataStore"""

    def __init__(self):
        self.redis_client: Optional[RedisClient] = None

    async def initialize(self):
        """Initialize Redis connection"""
        if self.redis_client is None:
            self.redis_client = await get_redis_connection()

    async def get_client(self) -> RedisClient:
        """
        Return an initialized Redis client

        Returns:
            Redis client instance

        Raises:
            ConnectionError: If Redis client not initialized
        """
        await self.initialize()
        if self.redis_client is None:
            raise ConnectionError("Redis client not initialized for MetadataStore")
        return self.redis_client

    async def cleanup(self):
        """Clean up Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
