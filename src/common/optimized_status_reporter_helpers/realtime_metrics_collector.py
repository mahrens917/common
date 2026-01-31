"""
Realtime message metrics collection from Redis sorted sets.

Aggregates Deribit and Kalshi message counts from the last 60 seconds
using ZRANGEBYSCORE for efficient time-windowed queries.
"""

import logging
import time
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.price_history_utils import parse_history_member_value
from common.redis_protocol.typing import ensure_awaitable
from common.redis_utils import RedisOperationError

logger = logging.getLogger(__name__)

REDIS_DATA_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    ValueError,
    TypeError,
    RuntimeError,
)


class RealtimeMetricsCollector:
    """Collects realtime message metrics from Redis history sorted sets."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client

    async def get_deribit_sum_last_60_seconds(self) -> int:
        """Get sum of Deribit updates from last 60 seconds."""
        return await self._sum_last_60s("history:deribit_realtime")

    async def get_kalshi_sum_last_60_seconds(self) -> int:
        """Get sum of Kalshi updates from last 60 seconds."""
        return await self._sum_last_60s("history:kalshi_realtime")

    async def _sum_last_60s(self, key: str) -> int:
        """Sum values in sorted set within last 60 seconds via ZRANGEBYSCORE."""
        try:
            redis_client = self.redis_client
            assert redis_client is not None, "Redis client required for realtime metrics"
            cutoff_time = time.time() - 60.0
            entries = await ensure_awaitable(redis_client.zrangebyscore(key, cutoff_time, "+inf", withscores=True))
            if not entries:
                return 0

            total_sum = 0.0
            for member, _score in entries:
                try:
                    total_sum += parse_history_member_value(member)
                except (  # policy_guard: allow-silent-handler
                    ValueError,
                    TypeError,
                ) as exc:
                    logger.debug("Error parsing realtime entry %r: %s", member, exc)
                    continue

            return int(round(total_sum))

        except REDIS_DATA_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.debug("Error getting %s sum last 60s (%s): %s", key, type(exc).__name__, exc)
            return 0
