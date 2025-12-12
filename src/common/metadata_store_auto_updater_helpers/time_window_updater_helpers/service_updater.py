"""Service-specific time window updates."""

import logging
from datetime import timedelta
from typing import Any, Optional

from common.redis_protocol.typing import RedisClient, ensure_awaitable

from .hash_validator import HashValidator

logger = logging.getLogger(__name__)
REDIS_ERRORS = (Exception,)


class ServiceUpdater:
    """Updates time-windowed counts for individual services."""

    def __init__(self, metadata_store, redis_client: RedisClient):
        """
        Initialize service updater.

        Args:
            metadata_store: Metadata store instance
            redis_client: Redis client instance
        """
        self.metadata_store = metadata_store
        self.redis_client = redis_client

    async def update_service_time_windows(self, service_name: str) -> None:
        """
        Update time-windowed counts for a specific service.

        Args:
            service_name: Name of service to update
        """
        try:
            history_key = f"history:{service_name}"
            if not await _ensure_supported_hash(self.redis_client, history_key, service_name):
                return

            from common.time_utils import get_current_utc

            current_time = get_current_utc()
            windows = _build_time_window_cutoffs(current_time)
            hash_data = await ensure_awaitable(self.redis_client.hgetall(history_key))
            counts = _calculate_window_counts(hash_data, windows)

            await _persist_counts(self.metadata_store, service_name, counts)
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Error updating time windows for %s: %s", service_name, exc, exc_info=True)


async def _ensure_supported_hash(redis_client: Optional[RedisClient], history_key: str, service_name: str) -> bool:
    """Validate that the redis key is a hash before processing."""
    if not await HashValidator.ensure_hash_history_key(redis_client, history_key):
        logger.warning("Skipping time window update for %s due to unsupported Redis type", service_name)
        return False
    return True


def _build_time_window_cutoffs(current_time):
    """Return strftime cutoffs for hour, 65 minutes, and 60 seconds ago."""
    return {
        "hour": (current_time - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "sixty_five_minutes": (current_time - timedelta(minutes=65)).strftime("%Y-%m-%d %H:%M:%S"),
        "sixty_seconds": (current_time - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S"),
    }


def _calculate_window_counts(hash_data: dict, windows: dict) -> dict:
    """Aggregate message counts per time window."""
    totals = {"hour": 0, "sixty_five_minutes": 0, "sixty_seconds": 0}
    for datetime_raw, count_raw in hash_data.items():
        datetime_str = _decode_if_needed(datetime_raw)
        count = _coerce_int(count_raw)

        if datetime_str >= windows["hour"]:
            totals["hour"] += count
        if datetime_str >= windows["sixty_five_minutes"]:
            totals["sixty_five_minutes"] += count
        if datetime_str >= windows["sixty_seconds"]:
            totals["sixty_seconds"] += count
    return totals


def _decode_if_needed(value: Any) -> Any:
    """Decode Redis bytes payloads."""
    return value.decode() if isinstance(value, bytes) else value


def _coerce_int(raw_value: Any) -> int:
    """Convert redis hash values into ints."""
    decoded = _decode_if_needed(raw_value)
    try:
        return int(decoded)
    except (TypeError, ValueError):  # policy_guard: allow-silent-handler
        return 0


async def _persist_counts(metadata_store, service_name: str, counts: dict) -> None:
    """Persist counts to metadata store with correct method per service type."""
    hour = counts["hour"]
    sixty_seconds = counts["sixty_seconds"]
    sixty_five_minutes = counts["sixty_five_minutes"]

    if service_name in ["asos", "metar"]:
        await metadata_store.update_weather_time_window_counts(service_name, hour, sixty_seconds, sixty_five_minutes)
        logger.debug(f"Updated weather time windows for {service_name}: hour={hour}, " f"60s={sixty_seconds}, 65m={sixty_five_minutes}")
        return

    await metadata_store.update_time_window_counts(service_name, hour, sixty_seconds)
    logger.debug(f"Updated time windows for {service_name}: hour={hour}, 60s={sixty_seconds}")
