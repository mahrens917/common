"""History data management"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from redis.exceptions import RedisError

from common.redis_protocol.config import HISTORY_KEY_PREFIX
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


class HistoryEntry(TypedDict):
    timestamp: datetime
    messages_per_second: float
    messages_per_minute: float


class HistoryManager:
    """Manages service history data"""

    async def get_service_history(self, client: RedisClient, service_name: str, hours: int = 24) -> List[HistoryEntry]:
        """
        Get service history for the specified time period

        Args:
            client: Redis client
            service_name: Name of the service
            hours: Number of hours of history to retrieve

        Returns:
            List of dictionaries with 'timestamp' and 'messages_per_second' keys
        """
        redis_key = f"{HISTORY_KEY_PREFIX}{service_name}"

        current_time = int(time.time())
        start_time = current_time - (hours * 3600)

        data = await _load_history_hash(client, redis_key, service_name)
        if not data:
            return []

        history_data = _parse_history_entries(data, start_time, service_name)
        history_data.sort(key=lambda x: x["timestamp"])
        return history_data


async def _load_history_hash(client: RedisClient, redis_key: str, service_name: str):
    """Fetch all history entries for a service."""
    try:
        return await ensure_awaitable(client.hgetall(redis_key))
    except REDIS_ERRORS as exc:  # pragma: no cover - network/runtime failure path
        raise RuntimeError(f"Failed to load history for service '{service_name}'") from exc


def _parse_history_entries(data: Dict[Any, Any], start_time: int, service_name: str) -> List[HistoryEntry]:
    """Parse hash entries into structured history data."""
    history_data: List[HistoryEntry] = []
    for key, value in data.items():
        entry = _parse_history_entry(key, value, service_name)
        if entry is None:
            continue

        timestamp, messages_per_minute = entry
        if timestamp < start_time:
            continue

        dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        history_data.append(
            {
                "timestamp": dt_obj,
                "messages_per_second": messages_per_minute,
                "messages_per_minute": messages_per_minute,
            }
        )
    return history_data


def _parse_history_entry(datetime_raw: Any, value_raw: Any, service_name: str) -> Optional[tuple[int, float]]:
    """Convert redis hash entry into (timestamp, value)."""
    datetime_str = _decode_if_bytes(datetime_raw)
    value_str = _decode_if_bytes(value_raw)
    try:
        timestamp = _coerce_timestamp(datetime_str)
        messages_per_minute = float(value_str)
    except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
        logger.warning(
            "Skipping invalid history data for %s: %s=%s (%s)",
            service_name,
            datetime_str,
            value_str,
            exc,
        )
        return None
    else:
        return timestamp, messages_per_minute


def _decode_if_bytes(value: Any) -> Any:
    """Decode Redis bytes values when necessary."""
    return value.decode() if isinstance(value, bytes) else value


def _coerce_timestamp(datetime_str: str) -> int:
    """Convert stored string to unix timestamp."""
    if "T" in datetime_str and "+" in datetime_str:
        dt = datetime.fromisoformat(datetime_str)
    else:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp())
