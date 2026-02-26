"""Redis history writer for message statistics using sorted sets."""

import logging

from ...price_history_utils import build_history_member
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
    Write message count to Redis sorted set for monitor consumption.

    Args:
        redis_client: Redis client instance
        service_name: Service name for key
        message_count: Number of messages in the last second
        current_time: Current timestamp

    Raises:
        ConnectionError: If Redis write fails
    """
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
