"""
Unified message statistics collector for WebSocket services.

Provides common message counting, rate calculation, and Redis history tracking
for both Deribit and Kalshi WebSocket services. Implements fail-fast error
handling for silent failures and Redis connectivity issues.
"""

import asyncio
import logging
import time
from typing import Optional

from ..price_history_utils import build_history_member
from ..redis_protocol.error_types import REDIS_ERRORS
from ..redis_protocol.typing import RedisClient, ensure_awaitable
from ..redis_utils import RedisOperationError, get_redis_connection

logger = logging.getLogger(__name__)

REDIS_WRITE_ERRORS = REDIS_ERRORS + (RedisOperationError, ConnectionError, RuntimeError, ValueError)


async def _write_message_count_to_redis(
    redis_client: RedisClient,
    service_name: str,
    message_count: int,
    current_time: float,
) -> None:
    try:
        int_ts = int(current_time)
        history_key = f"history:{service_name}"
        score = float(int_ts)
        member = build_history_member(int_ts, float(message_count))

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(history_key, score, score)
        pipe.zadd(history_key, {member: score})
        await ensure_awaitable(pipe.execute())

        logger.debug(f"{service_name.upper()}_HISTORY: Recorded {message_count} messages at ts={int_ts}")

    except REDIS_WRITE_ERRORS as exc:
        logger.exception("CRITICAL: Failed to record %s message count to Redis", service_name)
        raise ConnectionError(f"Redis write failure for {service_name}") from exc


def _check_silent_failure_threshold(
    current_rate: int,
    current_time: float,
    last_nonzero_update_time: float,
    threshold_seconds: int,
    service_name: str,
) -> bool:
    if current_rate > 0:
        return False

    time_since_last_update = current_time - last_nonzero_update_time
    if time_since_last_update <= threshold_seconds:
        return False

    logger.error("SILENT_FAILURE_DETECTION: No %s messages for %.1fs", service_name, time_since_last_update)
    return True


async def _send_silent_failure_alert(service_name: str, time_since_last_update: float) -> None:
    from common.alerter import Alerter, AlertSeverity

    try:
        alerter = Alerter()
        await alerter.send_alert(
            message=f"🔴 {service_name.upper()}_WS - Silent failure detected - No messages for {time_since_last_update:.1f}s",
            severity=AlertSeverity.CRITICAL,
            alert_type=f"{service_name}_ws_silent_failure",
        )
    except asyncio.CancelledError:
        raise
    except (
        RuntimeError,
        ConnectionError,
        OSError,
        ValueError,
        ImportError,
    ):  # Transient network/connection failure  # policy_guard: allow-silent-handler
        logger.debug(f"Silent failure alert not available: Alerter setup failed")


class MessageStatsCollector:
    """
    Unified message statistics collector with fail-fast error handling.

    Tracks message rates, detects silent failures, and maintains Redis history
    for monitoring systems. Raises exceptions on critical failures rather than
    silently continuing with degraded functionality.
    """

    def __init__(self, service_name: str, silent_failure_threshold_seconds: int = 120):
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
        threshold_exceeded = _check_silent_failure_threshold(
            self.current_rate,
            current_time,
            self._last_nonzero_update_time,
            self.silent_failure_threshold_seconds,
            self.service_name,
        )
        if threshold_exceeded:
            time_since_last_update = current_time - self._last_nonzero_update_time
            await _send_silent_failure_alert(self.service_name, time_since_last_update)
            raise ConnectionError(f"Silent failure detected: No {self.service_name} messages for {time_since_last_update:.1f}s")

    async def _write_to_history_redis(self, message_count: int, current_time: float) -> None:
        if self._redis_client is None:
            self._redis_client = await get_redis_connection()
        assert self._redis_client is not None, "Redis connection could not be established"
        await _write_message_count_to_redis(self._redis_client, self.service_name, message_count, current_time)

    def reset(self) -> None:
        self._message_count = 0
        self.current_rate = 0
        self._last_rate_time = time.time()
        self._last_nonzero_update_time = time.time()
