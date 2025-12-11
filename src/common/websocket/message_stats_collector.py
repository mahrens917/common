"""
Unified message statistics collector for WebSocket services.

Provides common message counting, rate calculation, and Redis history tracking
for both Deribit and Kalshi WebSocket services. Implements fail-fast error
handling for silent failures and Redis connectivity issues.
"""

import logging
import time
from typing import Optional

from ..redis_protocol.typing import RedisClient
from ..redis_utils import get_redis_connection
from .message_stats_helpers.redis_history_writer import write_message_count_to_redis
from .message_stats_helpers.silent_failure_alerter import (
    check_silent_failure_threshold,
    send_silent_failure_alert,
)

logger = logging.getLogger(__name__)


class MessageStatsCollector:
    """
    Unified message statistics collector with fail-fast error handling.

    Tracks message rates, detects silent failures, and maintains Redis history
    for monitoring systems. Raises exceptions on critical failures rather than
    silently continuing with degraded functionality.
    """

    def __init__(self, service_name: str, silent_failure_threshold_seconds: int = 120):
        """
        Initialize message statistics collector.

        Args:
            service_name: Name of the service (e.g., 'deribit', 'kalshi')
            silent_failure_threshold_seconds: Seconds without messages before raising exception
        """
        self.service_name = service_name
        self.silent_failure_threshold_seconds = silent_failure_threshold_seconds
        self._message_count = 0
        self._last_rate_time = time.time()
        self._last_nonzero_update_time = time.time()
        self.current_rate = 0
        self._redis_client: Optional[RedisClient] = None

    @property
    def last_nonzero_update_time(self) -> float:
        return self._last_nonzero_update_time

    def add_message(self) -> None:
        """Record a message update."""
        self._message_count += 1

    async def check_and_record_rate(self) -> None:
        current_time = time.time()
        if current_time - self._last_rate_time >= 1.0:
            self.current_rate = self._message_count
            if self.current_rate > 0:
                logger.info(
                    "%s_STATS: messages_per_sec=%s",
                    self.service_name.upper(),
                    self.current_rate,
                )
                self._last_nonzero_update_time = current_time
            await self._check_silent_failure(current_time)
            await self._write_to_history_redis(self.current_rate, current_time)
            self._message_count = 0
            self._last_rate_time = current_time

    async def _check_silent_failure(self, current_time: float) -> None:
        threshold_exceeded = check_silent_failure_threshold(
            self.current_rate,
            current_time,
            self._last_nonzero_update_time,
            self.silent_failure_threshold_seconds,
            self.service_name,
        )
        if threshold_exceeded:
            time_since_last_update = current_time - self._last_nonzero_update_time
            await send_silent_failure_alert(self.service_name, time_since_last_update)
            raise ConnectionError(f"Silent failure detected: No {self.service_name} messages for {time_since_last_update:.1f}s")

    async def _write_to_history_redis(self, message_count: int, current_time: float) -> None:
        if self._redis_client is None:
            self._redis_client = await get_redis_connection()
        assert self._redis_client is not None, "Redis connection could not be established"
        await write_message_count_to_redis(self._redis_client, self.service_name, message_count, current_time)

    def reset(self) -> None:
        self._message_count = 0
        self.current_rate = 0
        self._last_rate_time = time.time()
        self._last_nonzero_update_time = time.time()
