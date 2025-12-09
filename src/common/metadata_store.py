"""
MetadataStore for O(1) access to service activity counts

Provides fast access to service message counts without expensive KEYS operations.
Automatically maintained via Redis keyspace notifications.
"""

import logging
from typing import List, Optional, Set

from .metadata_store_helpers import ConnectionManager, OperationsFacade
from .metadata_store_helpers.history_manager import HistoryEntry
from .metadata_store_helpers.metadata_reader import ServiceMetadata

logger = logging.getLogger(__name__)


class MetadataStore:
    """
    Fast O(1) access to service activity metadata

    Maintains aggregated counts and activity metrics for all services
    without requiring expensive KEYS operations on history:* data.
    """

    def __init__(self):
        """Initialize metadata store"""
        self._connection = ConnectionManager()
        self._ops = OperationsFacade("metadata:service:", "metadata:global_stats")

    async def initialize(self):
        """Initialize Redis connection"""
        await self._connection.initialize()

    async def get_service_metadata(self, service_name: str) -> Optional[ServiceMetadata]:
        """Get metadata for a specific service with O(1) access"""
        client = await self._connection.get_client()
        return await self._ops.get_service_metadata(client, service_name)

    async def get_all_services(self) -> Set[str]:
        """Get set of all services that have metadata"""
        client = await self._connection.get_client()
        return await self._ops.get_all_services(client)

    async def get_total_message_count(self) -> int:
        """Get total message count across all services with O(1) access"""
        client = await self._connection.get_client()
        return await self._ops.get_total_message_count(client)

    async def increment_service_count(self, service_name: str, count: int = 1) -> bool:
        """Increment message count for a service"""
        client = await self._connection.get_client()
        return await self._ops.increment_service_count(client, service_name, count)

    async def update_time_window_counts(
        self, service_name: str, messages_last_hour: int, messages_last_minute: int
    ) -> bool:
        """Update time-windowed message counts for a service"""
        client = await self._connection.get_client()
        return await self._ops.update_time_window_counts(
            client, service_name, messages_last_hour, messages_last_minute
        )

    async def update_weather_time_window_counts(
        self,
        service_name: str,
        messages_last_hour: int,
        messages_last_minute: int,
        messages_last_65_minutes: int,
    ) -> bool:
        """Update time-windowed message counts for weather services (ASOS/METAR)"""
        client = await self._connection.get_client()
        return await self._ops.update_weather_time_window_counts(
            client, service_name, messages_last_hour, messages_last_minute, messages_last_65_minutes
        )

    async def initialize_service_count(self, service_name: str, initial_count: int) -> bool:
        """Initialize service count (used during startup reconciliation)"""
        client = await self._connection.get_client()
        return await self._ops.initialize_service_count(client, service_name, initial_count)

    async def get_service_history(self, service_name: str, hours: int = 24) -> List[HistoryEntry]:
        """Get service history for the specified time period"""
        client = await self._connection.get_client()
        return await self._ops.get_service_history(client, service_name, hours)

    async def cleanup(self):
        """Clean up Redis connection"""
        await self._connection.cleanup()
