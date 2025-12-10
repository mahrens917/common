"""Metadata writing operations"""

import logging
import time

from common.redis_protocol.typing import RedisClient

from .writer_operations import increment_metadata_counter, update_hash_fields

logger = logging.getLogger(__name__)


class MetadataWriter:
    """Handles writing metadata to Redis"""

    def __init__(self, metadata_key_prefix: str, global_stats_key: str):
        self.metadata_key_prefix = metadata_key_prefix
        self.global_stats_key = global_stats_key

    async def increment_service_count(
        self, client: RedisClient, service_name: str, count: int = 1
    ) -> bool:
        """Increment message count for a service"""
        metadata_key = f"{self.metadata_key_prefix}{service_name}"
        return await increment_metadata_counter(
            client, metadata_key, self.global_stats_key, service_name, count
        )

    async def update_time_window_counts(
        self,
        client: RedisClient,
        service_name: str,
        messages_last_hour: int,
        messages_last_minute: int,
    ) -> bool:
        """Update time-windowed message counts for a service"""
        metadata_key = f"{self.metadata_key_prefix}{service_name}"
        mapping = {
            "messages_last_hour": str(messages_last_hour),
            "messages_last_minute": str(messages_last_minute),
        }
        return await update_hash_fields(client, metadata_key, service_name, mapping)

    async def update_weather_time_window_counts(
        self,
        client: RedisClient,
        service_name: str,
        messages_last_hour: int,
        messages_last_minute: int,
        messages_last_65_minutes: int,
    ) -> bool:
        """Update time-windowed message counts for weather services"""
        metadata_key = f"{self.metadata_key_prefix}{service_name}"
        mapping = {
            "messages_last_hour": str(messages_last_hour),
            "messages_last_minute": str(messages_last_minute),
            "messages_last_65_minutes": str(messages_last_65_minutes),
        }
        return await update_hash_fields(client, metadata_key, service_name, mapping)

    async def initialize_service_count(
        self, client: RedisClient, service_name: str, initial_count: int
    ) -> bool:
        """Initialize service count (used during startup reconciliation)"""
        current_time = time.time()
        metadata_key = f"{self.metadata_key_prefix}{service_name}"
        mapping = {
            "total_count": str(initial_count),
            "last_activity": str(current_time),
            "messages_last_hour": "0",
            "messages_last_minute": "0",
        }
        result = await update_hash_fields(client, metadata_key, service_name, mapping)
        if result:
            logger.info(f"Initialized {service_name} metadata with count {initial_count}")
        return result
