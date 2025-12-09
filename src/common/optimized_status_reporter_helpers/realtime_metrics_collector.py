"""
Realtime message metrics collection from Redis.

Aggregates Deribit and Kalshi message counts from the last 60 seconds.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.common.redis_protocol.typing import ensure_awaitable
from src.common.redis_utils import RedisOperationError

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
    """Collects realtime message metrics from Redis history keys."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client

    async def get_deribit_sum_last_60_seconds(self) -> int:
        """Get sum of Deribit updates from last 60 seconds."""
        try:
            redis_client = self.redis_client
            assert redis_client is not None, "Redis client required for realtime metrics"
            all_entries = await ensure_awaitable(redis_client.hgetall("history:deribit_realtime"))
            if not all_entries:
                return 0

            current_time = time.time()
            cutoff_time = current_time - 60.0
            total_sum = 0

            for timestamp_str, count_str in all_entries.items():
                try:
                    timestamp = (
                        datetime.strptime(
                            (
                                timestamp_str.decode()
                                if isinstance(timestamp_str, bytes)
                                else timestamp_str
                            ),
                            "%Y-%m-%d %H:%M:%S",
                        )
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                    )

                    if timestamp >= cutoff_time:
                        total_sum += float(count_str)
                except (
                    ValueError,
                    TypeError,
                ) as exc:
                    logger.debug("Error parsing deribit realtime entry %s: %s", timestamp_str, exc)
                    continue

            return int(round(total_sum))

        except REDIS_DATA_ERRORS as exc:
            logger.debug("Error getting deribit sum last 60s (%s): %s", type(exc).__name__)
            return 0

    async def get_kalshi_sum_last_60_seconds(self) -> int:
        """Get sum of Kalshi updates from last 60 seconds."""
        try:
            redis_client = self.redis_client
            assert redis_client is not None, "Redis client required for realtime metrics"
            all_entries = await ensure_awaitable(redis_client.hgetall("history:kalshi_realtime"))
            if not all_entries:
                return 0

            current_time = time.time()
            cutoff_time = current_time - 60.0
            total_sum = 0

            for timestamp_str, count_str in all_entries.items():
                try:
                    timestamp = (
                        datetime.strptime(
                            (
                                timestamp_str.decode()
                                if isinstance(timestamp_str, bytes)
                                else timestamp_str
                            ),
                            "%Y-%m-%d %H:%M:%S",
                        )
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                    )

                    if timestamp >= cutoff_time:
                        total_sum += float(count_str)
                except (
                    ValueError,
                    TypeError,
                ) as exc:
                    logger.debug("Error parsing kalshi realtime entry %s: %s", timestamp_str, exc)
                    continue

            return int(round(total_sum))

        except REDIS_DATA_ERRORS as exc:
            logger.debug("Error getting kalshi sum last 60s (%s): %s", type(exc).__name__)
            return 0
