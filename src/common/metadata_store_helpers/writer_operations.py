"""Low-level Redis write operations for metadata"""

import asyncio
import logging
import time

from redis.exceptions import RedisError

from src.common.exceptions import DataError
from src.common.redis_protocol.config import HISTORY_TTL_SECONDS
from src.common.redis_protocol.typing import RedisClient, ensure_awaitable
from src.common.redis_utils import RedisOperationError

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


async def increment_metadata_counter(
    client: RedisClient,
    metadata_key: str,
    global_stats_key: str,
    service_name: str,
    count: int,
) -> bool:
    """
    Increment service counters in Redis

    Args:
        client: Redis client
        metadata_key: Service metadata key
        global_stats_key: Global stats key
        service_name: Service name for error messages
        count: Count to increment by

    Returns:
        True if successful

    Raises:
        RuntimeError: If Redis operation fails
    """
    current_time = time.time()

    pipe = client.pipeline()
    pipe.hincrby(metadata_key, "total_count", count)
    pipe.hset(metadata_key, "last_activity", str(current_time))
    pipe.expire(metadata_key, HISTORY_TTL_SECONDS)
    pipe.hincrby(global_stats_key, "total_messages", count)
    pipe.expire(global_stats_key, HISTORY_TTL_SECONDS)

    try:
        await ensure_awaitable(pipe.execute())
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise DataError(
            f"Failed to increment metadata counters for service '{service_name}'"
        ) from exc

    logger.debug(f"Incremented {service_name} count by {count}")
    return True


async def update_hash_fields(
    client: RedisClient, metadata_key: str, service_name: str, mapping: dict
) -> bool:
    """
    Update hash fields with error handling

    Args:
        client: Redis client
        metadata_key: Redis key to update
        service_name: Service name for error messages
        mapping: Field-value mapping to update

    Returns:
        True if successful

    Raises:
        RuntimeError: If Redis operation fails
    """
    try:
        await ensure_awaitable(client.hset(metadata_key, mapping=mapping))
        await ensure_awaitable(client.expire(metadata_key, HISTORY_TTL_SECONDS))
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise DataError(f"Failed to update metadata for service '{service_name}'") from exc

    return True
