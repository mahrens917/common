"""
Toggle Service Command API

Provides Redis-based command to trigger stopping or starting a service.
The UI writes a service name and action, monitor reads and clears it after execution.
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

TOGGLE_SERVICE_COMMAND_KEY = "config:command:toggle_service"
TOGGLE_SERVICE_RESULT_KEY = "config:command:toggle_service:result"
RESULT_TTL_SECONDS = 30


@dataclass
class ToggleServiceResult:
    """Result of toggle service command."""

    service_name: str
    action: str
    success: bool
    timestamp: str


async def request_toggle_service(redis: "Redis", service_name: str, action: str) -> None:
    """Request toggling a service by writing command to Redis.

    Args:
        redis: Redis client
        service_name: Name of the service to toggle
        action: "stop" or "start"
    """
    from common.time_utils import get_current_utc

    payload = json.dumps(
        {
            "service_name": service_name,
            "action": action,
            "timestamp": get_current_utc().isoformat(),
        }
    )
    await ensure_awaitable(redis.set(TOGGLE_SERVICE_COMMAND_KEY, payload))
    logger.info("Toggle service command issued: %s %s", action, service_name)


async def get_toggle_service_command(redis: "Redis") -> Optional[Tuple[str, str, str]]:
    """Get the toggle service command if present.

    Args:
        redis: Redis client

    Returns:
        Tuple of (service_name, action, timestamp) if command is pending, None otherwise
    """
    value = await ensure_awaitable(redis.get(TOGGLE_SERVICE_COMMAND_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    data = json.loads(value)
    return data["service_name"], data["action"], data["timestamp"]


async def clear_toggle_service_command(redis: "Redis") -> None:
    """Clear the toggle service command after execution.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(TOGGLE_SERVICE_COMMAND_KEY))
    logger.info("Toggle service command cleared")


async def write_toggle_service_result(redis: "Redis", service_name: str, action: str, success: bool) -> None:
    """Write the result of toggle service command.

    Args:
        redis: Redis client
        service_name: Name of the service that was toggled
        action: "stop" or "start"
        success: Whether the toggle succeeded
    """
    from common.time_utils import get_current_utc

    result = {
        "service_name": service_name,
        "action": action,
        "success": success,
        "timestamp": get_current_utc().isoformat(),
    }
    await ensure_awaitable(redis.set(TOGGLE_SERVICE_RESULT_KEY, json.dumps(result), ex=RESULT_TTL_SECONDS))
    logger.info("Toggle service result written: %s %s success=%s", action, service_name, success)


async def get_toggle_service_result(redis: "Redis") -> Optional[ToggleServiceResult]:
    """Get the result of toggle service command if available.

    Args:
        redis: Redis client

    Returns:
        ToggleServiceResult if result exists, None otherwise
    """
    value = await ensure_awaitable(redis.get(TOGGLE_SERVICE_RESULT_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    data = json.loads(value)
    return ToggleServiceResult(
        service_name=data["service_name"],
        action=data["action"],
        success=data["success"],
        timestamp=data["timestamp"],
    )


async def clear_toggle_service_result(redis: "Redis") -> None:
    """Clear the toggle service result.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(TOGGLE_SERVICE_RESULT_KEY))


DISABLED_SERVICES_KEY = "config:disabled_services"


async def mark_service_disabled(redis: "Redis", service_name: str) -> None:
    """Mark a service as intentionally disabled (suppresses auto-heal)."""
    await ensure_awaitable(redis.sadd(DISABLED_SERVICES_KEY, service_name))
    logger.info("Marked service as disabled: %s", service_name)


async def mark_service_enabled(redis: "Redis", service_name: str) -> None:
    """Remove intentional-disable mark so auto-heal can manage the service again."""
    await ensure_awaitable(redis.srem(DISABLED_SERVICES_KEY, service_name))
    logger.info("Marked service as enabled: %s", service_name)


async def is_service_disabled(redis: "Redis", service_name: str) -> bool:
    """Check whether a service has been intentionally disabled."""
    result = await ensure_awaitable(redis.sismember(DISABLED_SERVICES_KEY, service_name))
    return bool(result)


__all__ = [
    "DISABLED_SERVICES_KEY",
    "TOGGLE_SERVICE_COMMAND_KEY",
    "TOGGLE_SERVICE_RESULT_KEY",
    "ToggleServiceResult",
    "clear_toggle_service_command",
    "clear_toggle_service_result",
    "get_toggle_service_command",
    "get_toggle_service_result",
    "is_service_disabled",
    "mark_service_disabled",
    "mark_service_enabled",
    "request_toggle_service",
    "write_toggle_service_result",
]
