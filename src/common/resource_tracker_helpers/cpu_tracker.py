"""CPU usage tracking for ResourceTracker."""

import logging
import time
from typing import List, Tuple

from redis.asyncio import Redis

from ..redis_protocol import config
from ..redis_protocol.error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class CpuTracker:
    """Handles CPU usage recording and history retrieval."""

    def __init__(self, redis: Redis):
        """Initialize CPU tracker."""
        self.redis = redis

    async def record_cpu_usage(self, total_cpu_percent: float) -> bool:
        """
        Record total CPU usage across all processes.

        Args:
            total_cpu_percent: Total CPU percentage across all processes

        Returns:
            True if successfully recorded, False otherwise
        """
        try:
            timestamp = int(time.time() * 1000)
            key = f"{config.HISTORY_KEY_PREFIX}cpu_total"
            member = f"{timestamp}:{total_cpu_percent}"

            await self.redis.zadd(key, {member: timestamp})
            await self.redis.expire(key, config.HISTORY_TTL_SECONDS)

            cutoff_time = timestamp - (config.HISTORY_TTL_SECONDS * 1000)
            await self.redis.zremrangebyscore(key, 0, cutoff_time)

            logger.debug(f"Recorded {total_cpu_percent}% total CPU usage at {timestamp}")

        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error recording CPU usage: %s", exc, exc_info=True)
            return False
        else:
            return True

    async def get_cpu_history(self, hours: int = 24) -> List[Tuple[int, float]]:
        """
        Get CPU usage history.

        Args:
            hours: Number of hours of history to retrieve (default: 24)

        Returns:
            List of (timestamp, cpu_percent) tuples, sorted by timestamp
        """
        try:
            current_time = int(time.time() * 1000)
            start_time = current_time - (hours * 3600 * 1000)
            key = f"{config.HISTORY_KEY_PREFIX}cpu_total"

            result = await self.redis.zrangebyscore(key, start_time, current_time, withscores=False)

            history = []
            for member in result:
                try:
                    member_str = str(member)
                    timestamp_str, value_str = member_str.split(":", 1)
                    timestamp_sec = int(timestamp_str) // 1000
                    cpu_percent = float(value_str)
                    history.append((timestamp_sec, cpu_percent))
                except (  # policy_guard: allow-silent-handler
                    ValueError,
                    IndexError,
                ) as parse_error:
                    logger.warning(f"Invalid member format: {member}, error: {parse_error}")
                    continue

            history.sort(key=lambda x: x[0])
            logger.debug(f"Retrieved {len(history)} CPU history entries over {hours} hours")

        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error getting CPU history: %s", exc, exc_info=True)
            return []
        else:
            return history
