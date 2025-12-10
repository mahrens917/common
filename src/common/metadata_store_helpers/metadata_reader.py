"""Metadata reading operations"""

import logging
from typing import Optional, Set

from common.exceptions import DataError
from common.redis_protocol.typing import RedisClient

from .data_normalizer import DataNormalizer
from .reader_operations import fetch_hash_data, fetch_hash_field, fetch_service_keys

logger = logging.getLogger(__name__)


class ServiceMetadata:
    """Metadata for a single service"""

    def __init__(
        self,
        service_name: str,
        total_message_count: int,
        last_activity_timestamp: float,
        messages_last_hour: int,
        messages_last_minute: int,
        messages_last_65_minutes: int,
    ):
        self.service_name = service_name
        self.total_message_count = total_message_count
        self.last_activity_timestamp = last_activity_timestamp
        self.messages_last_hour = messages_last_hour
        self.messages_last_minute = messages_last_minute
        self.messages_last_65_minutes = messages_last_65_minutes


class MetadataReader:
    """Handles reading metadata from Redis"""

    def __init__(self, metadata_key_prefix: str, global_stats_key: str):
        self.metadata_key_prefix = metadata_key_prefix
        self.global_stats_key = global_stats_key
        self.normalizer = DataNormalizer()

    async def get_service_metadata(
        self, client: RedisClient, service_name: str
    ) -> Optional[ServiceMetadata]:
        """Get metadata for a specific service with O(1) access"""
        metadata_key = f"{self.metadata_key_prefix}{service_name}"
        metadata_data = await fetch_hash_data(
            client, metadata_key, f"metadata for service '{service_name}'"
        )

        if not metadata_data:
            return None

        try:
            normalized = self.normalizer.normalize_hash(metadata_data)
            return ServiceMetadata(
                service_name=service_name,
                total_message_count=self.normalizer.int_field(normalized, "total_count", default=0),
                last_activity_timestamp=self.normalizer.float_field(
                    normalized, "last_activity", default=0.0
                ),
                messages_last_hour=self.normalizer.int_field(
                    normalized, "messages_last_hour", default=0
                ),
                messages_last_minute=self.normalizer.int_field(
                    normalized, "messages_last_minute", default=0
                ),
                messages_last_65_minutes=self.normalizer.int_field(
                    normalized, "messages_last_65_minutes", default=0
                ),
            )
        except (TypeError, ValueError) as exc:
            raise DataError(
                f"Metadata for service '{service_name}' is corrupt: {metadata_data}"
            ) from exc

    async def get_all_services(self, client: RedisClient) -> Set[str]:
        """Get set of all services that have metadata"""
        pattern = f"{self.metadata_key_prefix}*"
        keys = await fetch_service_keys(client, pattern)

        services: Set[str] = set()
        for key in keys:
            services.add(key.replace(self.metadata_key_prefix, ""))

        return services

    async def get_total_message_count(self, client: RedisClient) -> int:
        """Get total message count across all services with O(1) access"""
        total_str = await fetch_hash_field(
            client, self.global_stats_key, "total_messages", "total message count"
        )

        if total_str is None:
            return 0

        try:
            return int(total_str)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"Global message count is not an integer: {total_str!r}") from exc
