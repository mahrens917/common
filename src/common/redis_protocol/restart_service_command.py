"""
Restart Service Command API

Provides Redis-based command to trigger restarting a service.
The UI writes a service name, monitor reads and clears it after execution.
Monitor writes result back for UI to display.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple

from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

RESTART_SERVICE_COMMAND_KEY = "config:command:restart_service"
RESTART_SERVICE_RESULT_KEY = "config:command:restart_service:result"
RESULT_TTL_SECONDS = 30


@dataclass
class RestartServiceResult:
    """Result of restart service command."""

    service_name: str
    success: bool
    timestamp: str


async def request_restart_service(redis: "Redis", service_name: str) -> None:
    """Request restarting a service by writing command to Redis.

    Args:
        redis: Redis client
        service_name: Name of the service to restart
    """
    from common.time_utils import get_current_utc

    payload = json.dumps({"service_name": service_name, "timestamp": get_current_utc().isoformat()})
    await ensure_awaitable(redis.set(RESTART_SERVICE_COMMAND_KEY, payload))
    logger.info("Restart service command issued for %s", service_name)


async def get_restart_service_command(redis: "Redis") -> Optional[Tuple[str, str]]:
    """Get the restart service command if present.

    Args:
        redis: Redis client

    Returns:
        Tuple of (service_name, timestamp) if command is pending, None otherwise
    """
    value = await ensure_awaitable(redis.get(RESTART_SERVICE_COMMAND_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    data = json.loads(value)
    return data["service_name"], data["timestamp"]


async def clear_restart_service_command(redis: "Redis") -> None:
    """Clear the restart service command after execution.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(RESTART_SERVICE_COMMAND_KEY))
    logger.info("Restart service command cleared")


async def write_restart_service_result(redis: "Redis", service_name: str, success: bool) -> None:
    """Write the result of restart service command.

    Args:
        redis: Redis client
        service_name: Name of the service that was restarted
        success: Whether the restart succeeded
    """
    from common.time_utils import get_current_utc

    result = {
        "service_name": service_name,
        "success": success,
        "timestamp": get_current_utc().isoformat(),
    }
    await ensure_awaitable(redis.set(RESTART_SERVICE_RESULT_KEY, json.dumps(result), ex=RESULT_TTL_SECONDS))
    logger.info("Restart service result written: %s success=%s", service_name, success)


async def get_restart_service_result(redis: "Redis") -> Optional[RestartServiceResult]:
    """Get the result of restart service command if available.

    Args:
        redis: Redis client

    Returns:
        RestartServiceResult if result exists, None otherwise
    """
    value = await ensure_awaitable(redis.get(RESTART_SERVICE_RESULT_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    data = json.loads(value)
    return RestartServiceResult(
        service_name=data["service_name"],
        success=data["success"],
        timestamp=data["timestamp"],
    )


async def clear_restart_service_result(redis: "Redis") -> None:
    """Clear the restart service result.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(RESTART_SERVICE_RESULT_KEY))


__all__ = [
    "RESTART_SERVICE_COMMAND_KEY",
    "RESTART_SERVICE_RESULT_KEY",
    "RestartServiceResult",
    "clear_restart_service_command",
    "clear_restart_service_result",
    "get_restart_service_command",
    "get_restart_service_result",
    "request_restart_service",
    "write_restart_service_result",
]
