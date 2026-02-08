"""Service-specific time window updates using sorted set queries."""

import logging
from datetime import timedelta
from typing import Any, Optional

from common.price_history_utils import parse_history_member_value
from common.redis_protocol.typing import RedisClient, ensure_awaitable

from .hash_validator import HistoryKeyValidator

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
            if not await _ensure_supported_sorted_set(self.redis_client, history_key, service_name):
                return

            from common.time_utils import get_current_utc

            current_time = get_current_utc()
            current_ts = current_time.timestamp()
            cutoffs = _build_timestamp_cutoffs(current_ts)
            broadest_cutoff = cutoffs["sixty_five_minutes"]
            entries = await ensure_awaitable(self.redis_client.zrangebyscore(history_key, broadest_cutoff, "+inf", withscores=True))
            counts = _calculate_window_counts(entries, cutoffs)

            await _persist_counts(self.metadata_store, service_name, counts)
        except REDIS_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.error("Error updating time windows for %s: %s", service_name, exc, exc_info=True)


async def _ensure_supported_sorted_set(redis_client: Optional[RedisClient], history_key: str, service_name: str) -> bool:
    """Validate that the redis key is a sorted set before processing."""
    if not await HistoryKeyValidator.ensure_sorted_set_history_key(redis_client, history_key):
        logger.warning("Skipping time window update for %s due to unsupported Redis type", service_name)
        return False
    return True


def _build_timestamp_cutoffs(current_ts: float) -> dict[str, float]:
    """Return unix timestamp cutoffs for hour, 65 minutes, and 60 seconds ago."""
    return {
        "hour": current_ts - 3600,
        "sixty_five_minutes": current_ts - 3900,
        "sixty_seconds": current_ts - 60,
    }


def _calculate_window_counts(entries: list, cutoffs: dict[str, float]) -> dict:
    """Aggregate message counts per time window from sorted set entries."""
    totals = {"hour": 0, "sixty_five_minutes": 0, "sixty_seconds": 0}
    for member, score in entries:
        count = _coerce_int_from_member(member)
        totals["sixty_five_minutes"] += count
        if score >= cutoffs["hour"]:
            totals["hour"] += count
        if score >= cutoffs["sixty_seconds"]:
            totals["sixty_seconds"] += count
    return totals


def _coerce_int_from_member(member: Any) -> int:
    """Extract integer value from a sorted set member."""
    try:
        return int(parse_history_member_value(member))
    except (TypeError, ValueError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse member value: member=%r, error=%s", member, exc)
        return 0


async def _persist_counts(metadata_store, service_name: str, counts: dict) -> None:
    """Persist counts to metadata store with correct method per service type."""
    hour = counts["hour"]
    sixty_seconds = counts["sixty_seconds"]
    sixty_five_minutes = counts["sixty_five_minutes"]

    if service_name == "asos":
        await metadata_store.update_weather_time_window_counts(service_name, hour, sixty_seconds, sixty_five_minutes)
        logger.debug(f"Updated weather time windows for {service_name}: hour={hour}, " f"60s={sixty_seconds}, 65m={sixty_five_minutes}")
        return

    await metadata_store.update_time_window_counts(service_name, hour, sixty_seconds)
    logger.debug(f"Updated time windows for {service_name}: hour={hour}, 60s={sixty_seconds}")
