"""
Close Positions Command API

Provides Redis-based command to trigger closing all positions.
The UI writes a timestamp, tracker reads and clears it after execution.
Tracker writes result back for UI to display.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .streams import CLOSE_POSITIONS_STREAM, stream_publish
from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

CLOSE_POSITIONS_COMMAND_KEY = "config:command:close_positions"
CLOSE_POSITIONS_RESULT_KEY = "config:command:close_positions:result"
RESULT_TTL_SECONDS = 30
COMMAND_TTL_SECONDS = 60


@dataclass
class ClosePositionsResult:
    """Result of close all positions command."""

    closed_count: int
    total_count: int
    timestamp: str


async def request_close_all_positions(redis: "Redis") -> None:
    """
    Request closing all positions by writing current timestamp to Redis.

    The command key is the source of truth; the stream notification
    guarantees the subscriber wakes up even if it was offline when
    the command was issued.

    Args:
        redis: Redis client
    """
    from common.time_utils import get_current_utc

    timestamp = get_current_utc().isoformat()
    await ensure_awaitable(redis.set(CLOSE_POSITIONS_COMMAND_KEY, timestamp, ex=COMMAND_TTL_SECONDS))
    await stream_publish(redis, CLOSE_POSITIONS_STREAM, {"timestamp": timestamp, "action": "close_all"})
    logger.info("Close all positions command issued at %s", timestamp)


async def get_close_positions_command(redis: "Redis") -> Optional[str]:
    """
    Get the close positions command timestamp if present.

    Args:
        redis: Redis client

    Returns:
        ISO timestamp string if command is pending, None otherwise
    """
    value = await ensure_awaitable(redis.get(CLOSE_POSITIONS_COMMAND_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value)


async def clear_close_positions_command(redis: "Redis") -> None:
    """
    Clear the close positions command after execution.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(CLOSE_POSITIONS_COMMAND_KEY))
    logger.info("Close all positions command cleared")


async def write_close_positions_result(
    redis: "Redis",
    closed_count: int,
    total_count: int,
) -> None:
    """
    Write the result of close all positions command.

    Args:
        redis: Redis client
        closed_count: Number of positions successfully closed
        total_count: Total number of positions attempted
    """
    from common.time_utils import get_current_utc

    result = {
        "closed_count": closed_count,
        "total_count": total_count,
        "timestamp": get_current_utc().isoformat(),
    }
    await ensure_awaitable(redis.set(CLOSE_POSITIONS_RESULT_KEY, json.dumps(result), ex=RESULT_TTL_SECONDS))
    logger.info("Close positions result written: %d/%d closed", closed_count, total_count)


async def get_close_positions_result(redis: "Redis") -> Optional[ClosePositionsResult]:
    """
    Get the result of close all positions command if available.

    Args:
        redis: Redis client

    Returns:
        ClosePositionsResult if result exists, None otherwise
    """
    value = await ensure_awaitable(redis.get(CLOSE_POSITIONS_RESULT_KEY))
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    data = json.loads(value)
    return ClosePositionsResult(
        closed_count=data["closed_count"],
        total_count=data["total_count"],
        timestamp=data["timestamp"],
    )


async def clear_close_positions_result(redis: "Redis") -> None:
    """
    Clear the close positions result.

    Args:
        redis: Redis client
    """
    await ensure_awaitable(redis.delete(CLOSE_POSITIONS_RESULT_KEY))


__all__ = [
    "CLOSE_POSITIONS_COMMAND_KEY",
    "CLOSE_POSITIONS_RESULT_KEY",
    "ClosePositionsResult",
    "clear_close_positions_command",
    "clear_close_positions_result",
    "get_close_positions_command",
    "get_close_positions_result",
    "request_close_all_positions",
    "write_close_positions_result",
]
