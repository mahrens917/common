"""
Reconnection event management for ConnectionStore
"""

import json
import logging
import time
from typing import Any, Dict, List

from ..error_types import JSON_ERRORS, REDIS_ERRORS, SERIALIZATION_ERRORS
from ..typing import ensure_awaitable

logger = logging.getLogger(__name__)


class ReconnectionEventManager:
    """Manages reconnection event recording and retrieval"""

    def __init__(self, redis_getter, reconnection_events_key: str):
        """
        Initialize reconnection event manager

        Args:
            redis_getter: Async function that returns Redis client
            reconnection_events_key: Redis key for reconnection events sorted set
        """
        self._get_client = redis_getter
        self.reconnection_events_key = reconnection_events_key

    async def record_reconnection_event(self, service_name: str, event_type: str, details: str = "") -> None:
        """
        Record a reconnection event for debugging and monitoring.

        Args:
            service_name: Name of the service
            event_type: Type of event (start, success, failure)
            details: Additional event details
        """
        try:
            client = await self._get_client()
            event_data = {
                "service_name": service_name,
                "event_type": event_type,
                "timestamp": time.time(),
                "details": details,
            }
            event_json = json.dumps(event_data)
        except SERIALIZATION_ERRORS:  # policy_guard: allow-silent-handler
            logger.error(
                "Failed to serialise reconnection event for %s",
                service_name,
                exc_info=True,
            )
            return

        try:
            await ensure_awaitable(client.zadd(self.reconnection_events_key, {event_json: time.time()}))
            cutoff_time = time.time() - 86400
            await ensure_awaitable(client.zremrangebyscore(self.reconnection_events_key, 0, cutoff_time))
            logger.debug("Recorded reconnection event for %s: %s", service_name, event_type)
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.error(
                "Failed to record reconnection event for %s",
                service_name,
                exc_info=True,
            )

    async def get_recent_reconnection_events(self, service_name: str, hours_back: int = 1) -> List[Dict[str, Any]]:
        """
        Get recent reconnection events for a service.

        Args:
            service_name: Name of the service
            hours_back: How many hours back to look

        Returns:
            List of reconnection events
        """
        try:
            client = await self._get_client()
            cutoff_time = time.time() - (hours_back * 3600)
            events = await ensure_awaitable(client.zrangebyscore(self.reconnection_events_key, cutoff_time, "+inf"))
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.error(
                "Failed to get reconnection events for %s",
                service_name,
                exc_info=True,
            )
            return []

        service_events: List[Dict[str, Any]] = []
        for event_json in events:
            try:
                event_data = json.loads(event_json)
            except JSON_ERRORS as exc:  # policy_guard: allow-silent-handler
                logger.warning("Failed to parse reconnection event payload: %s", exc)
                continue

            if event_data.get("service_name") == service_name:
                service_events.append(event_data)

        return sorted(service_events, key=lambda event: event["timestamp"])
