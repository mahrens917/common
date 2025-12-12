"""Status writing logic for StatusReporterMixin."""

import asyncio
import logging
import time
from typing import Any, Dict

from redis.asyncio import Redis
from redis.exceptions import RedisError

from common.redis_protocol.typing import ensure_awaitable
from common.service_status import ServiceStatus

logger = logging.getLogger(__name__)


async def write_status_to_redis(
    redis: Redis,
    status_key: str,
    service_name: str,
    status: ServiceStatus,
    pid: int,
    start_time: float,
    additional_fields: Dict[str, Any],
) -> None:
    """
    Write service status to Redis using unified pattern.

    Args:
        redis: Redis client
        status_key: Redis key for status hash
        service_name: Service name
        status: ServiceStatus enum value
        pid: Process ID
        start_time: Service start timestamp
        additional_fields: Service-specific metrics/fields

    Raises:
        Exception: If Redis write fails
    """
    current_time = time.time()
    uptime = current_time - start_time

    status_data: Dict[str, Any] = {
        "status": status.value,
        "timestamp": current_time,
        "pid": pid,
        "uptime_seconds": uptime,
        **additional_fields,
    }

    try:
        # Write to unified pattern (ops:status:<service>)
        await ensure_awaitable(
            redis.hset(
                status_key,
                mapping={k: str(v) for k, v in status_data.items()},
            )
        )
        # Legacy pattern for backwards compatibility (status hash)
        await ensure_awaitable(redis.hset("status", service_name, status.value))

        logger.info(
            "Status updated",
            extra={
                "service": service_name,
                "status": status.value,
                "pid": pid,
                "uptime_seconds": round(uptime, 2),
                **additional_fields,
            },
        )

    except asyncio.CancelledError:
        raise
    except (RedisError, ConnectionError, OSError) as exc:  # policy_guard: allow-silent-handler
        logger.exception(
            "Failed to report status to Redis",
            extra={
                "service": service_name,
                "status": status.value,
            },
        )
        raise RuntimeError(f"Redis status write failed: {exc}") from exc


__all__ = ["write_status_to_redis"]
