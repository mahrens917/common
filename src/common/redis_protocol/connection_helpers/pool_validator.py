"""
Redis pool connection validation.

Why: Separates pool testing logic from pool creation
How: Tests pool connectivity with timeouts and extracts server info
"""

import asyncio
import logging

import redis.asyncio
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Error types that can occur during Redis setup
REDIS_SETUP_ERRORS = (
    RedisError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
    RuntimeError,
    ValueError,
)


async def test_pool_connection(pool: redis.asyncio.ConnectionPool, host: str, port: int, db: int) -> None:
    """
    Test Redis pool by creating a temporary connection and pinging server.

    Args:
        pool: Connection pool to test
        host: Redis host for error messages
        port: Redis port for error messages
        db: Redis database for error messages

    Raises:
        RuntimeError: If connection test fails or times out
    """
    test_client = None
    try:
        test_client = redis.asyncio.Redis(connection_pool=pool)
        await asyncio.wait_for(test_client.ping(), timeout=5.0)
        await _log_server_info(test_client)
    except asyncio.TimeoutError as exc:  # policy_guard: allow-silent-handler
        logger.exception(f"Redis connection test timed out after 5 seconds: ")
        logger.exception(f"Attempted connection to: :/{db}")
        raise RuntimeError(f"Redis connection test timed out - Redis server may not be available at {host}:{port}") from exc
    except REDIS_SETUP_ERRORS as exc:  # policy_guard: allow-silent-handler
        logger.exception("Error testing Redis connection: %s: %s", type(exc).__name__)
        logger.exception(f"Attempted connection to: :/{db}")
        logger.exception(f"Pool settings used: host=, port=, db={db}")
        raise RuntimeError(f"Redis pool creation failed: {type(exc).__name__}") from exc
    finally:
        if test_client:
            await test_client.aclose()


# Prevent pytest from collecting helper as a standalone test
setattr(test_pool_connection, "__test__", False)


async def _log_server_info(client: redis.asyncio.Redis) -> None:
    """
    Log Redis server version and mode information.

    Args:
        client: Connected Redis client

    Raises:
        RuntimeError: If server info cannot be retrieved
    """
    try:
        info = await asyncio.wait_for(client.info(), timeout=5.0)
    except (asyncio.TimeoutError, *REDIS_SETUP_ERRORS) as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"Failed to retrieve Redis server info: {exc}") from exc

    version = info.get("redis_version")
    if version is None:
        raise RuntimeError("Redis server info missing required 'redis_version' field")
    logger.info(f"Redis server version: {version}")

    mode = info.get("redis_mode")
    if mode is None:
        raise RuntimeError("Redis server info missing required 'redis_mode' field")
    logger.info(f"Redis server mode: {mode}")
