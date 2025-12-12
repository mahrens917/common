"""Redis history writer for message statistics"""

import logging
from datetime import datetime, timezone

from ...redis_protocol.error_types import REDIS_ERRORS
from ...redis_protocol.typing import RedisClient, ensure_awaitable
from ...redis_utils import RedisOperationError

logger = logging.getLogger(__name__)

REDIS_WRITE_ERRORS = REDIS_ERRORS + (RedisOperationError, ConnectionError, RuntimeError, ValueError)


async def write_message_count_to_redis(
    redis_client: RedisClient,
    service_name: str,
    message_count: int,
    current_time: float,
) -> None:
    """
    Write message count to Redis history for monitor consumption.

    Args:
        redis_client: Redis client instance
        service_name: Service name for key
        message_count: Number of messages in the last second
        current_time: Current timestamp

    Raises:
        ConnectionError: If Redis write fails
    """
    try:
        datetime_str = datetime.fromtimestamp(current_time, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        history_key = f"history:{service_name}"
        await ensure_awaitable(redis_client.hset(history_key, datetime_str, str(message_count)))
        await ensure_awaitable(redis_client.expire(history_key, 86400))  # 24 hours

        logger.debug(f"{service_name.upper()}_HISTORY: Recorded {message_count} messages at {datetime_str}")

    except REDIS_WRITE_ERRORS as exc:  # policy_guard: allow-silent-handler
        logger.exception("CRITICAL: Failed to record %s message count to Redis", service_name)
        raise ConnectionError(f"Redis write failure for {service_name}") from exc
