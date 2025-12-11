"""Unified facade for all metadata operations"""

import logging
from typing import List, Optional, Set

from common.redis_protocol.typing import RedisClient

from .history_manager import HistoryEntry, HistoryManager
from .metadata_reader import MetadataReader, ServiceMetadata
from .metadata_writer import MetadataWriter

logger = logging.getLogger(__name__)


class OperationsFacade:
    """Unified interface for all metadata operations"""

    def __init__(self, metadata_key_prefix: str, global_stats_key: str):
        self.reader = MetadataReader(metadata_key_prefix, global_stats_key)
        self.writer = MetadataWriter(metadata_key_prefix, global_stats_key)
        self.history = HistoryManager()

    async def get_service_metadata(self, client: RedisClient, service_name: str) -> Optional[ServiceMetadata]:
        """Get metadata for a specific service"""
        return await self.reader.get_service_metadata(client, service_name)

    async def get_all_services(self, client: RedisClient) -> Set[str]:
        """Get set of all services that have metadata"""
        return await self.reader.get_all_services(client)

    async def get_total_message_count(self, client: RedisClient) -> int:
        """Get total message count across all services"""
        return await self.reader.get_total_message_count(client)

    async def increment_service_count(self, client: RedisClient, service_name: str, count: int = 1) -> bool:
        """Increment message count for a service"""
        return await self.writer.increment_service_count(client, service_name, count)

    async def update_time_window_counts(
        self,
        client: RedisClient,
        service_name: str,
        messages_last_hour: int,
        messages_last_minute: int,
    ) -> bool:
        """Update time-windowed message counts for a service"""
        return await self.writer.update_time_window_counts(client, service_name, messages_last_hour, messages_last_minute)

    async def update_weather_time_window_counts(
        self,
        client: RedisClient,
        service_name: str,
        messages_last_hour: int,
        messages_last_minute: int,
        messages_last_65_minutes: int,
    ) -> bool:
        """Update time-windowed message counts for weather services"""
        return await self.writer.update_weather_time_window_counts(
            client, service_name, messages_last_hour, messages_last_minute, messages_last_65_minutes
        )

    async def initialize_service_count(self, client: RedisClient, service_name: str, initial_count: int) -> bool:
        """Initialize service count (used during startup reconciliation)"""
        return await self.writer.initialize_service_count(client, service_name, initial_count)

    async def get_service_history(self, client: RedisClient, service_name: str, hours: int = 24) -> List[HistoryEntry]:
        """Get service history for the specified time period"""
        return await self.history.get_service_history(client, service_name, hours)
