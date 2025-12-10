"""Low-level Redis read operations for metadata"""

import asyncio
import logging
from typing import Dict, Optional, Set

from redis.exceptions import RedisError

from common.exceptions import DataError
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_utils import RedisOperationError

logger = logging.getLogger(__name__)

REDIS_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


async def fetch_hash_data(client: RedisClient, key: str, error_context: str) -> Optional[Dict]:
    """
    Fetch hash data from Redis with error handling

    Args:
        client: Redis client
        key: Redis key to fetch
        error_context: Context string for error messages

    Returns:
        Hash data or None if key doesn't exist

    Raises:
        RuntimeError: If Redis operation fails
    """
    try:
        data = await ensure_awaitable(client.hgetall(key))
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise RuntimeError(f"Failed to fetch {error_context}") from exc

    return data if data else None


async def fetch_service_keys(client: RedisClient, pattern: str) -> Set[str]:
    """
    Fetch all keys matching a pattern

    Args:
        client: Redis client
        pattern: Key pattern to match

    Returns:
        Set of decoded key strings

    Raises:
        RuntimeError: If Redis operation fails
    """
    try:
        keys = await ensure_awaitable(client.keys(pattern))
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise DataError("Failed to enumerate metadata services") from exc

    decoded_keys: Set[str] = set()
    for key in keys:
        decoded = key.decode() if isinstance(key, bytes) else key
        decoded_keys.add(decoded)

    return decoded_keys


async def fetch_hash_field(
    client: RedisClient, key: str, field: str, error_context: str
) -> Optional[str]:
    """
    Fetch a single hash field from Redis

    Args:
        client: Redis client
        key: Redis key
        field: Hash field name
        error_context: Context string for error messages

    Returns:
        Field value or None if field doesn't exist

    Raises:
        RuntimeError: If Redis operation fails
    """
    try:
        value = await ensure_awaitable(client.hget(key, field))
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise RuntimeError(f"Failed to read {error_context}") from exc

    return value
