"""Service name extraction from Redis keys"""

import logging
import re
from typing import Optional, Set

logger = logging.getLogger(__name__)


# Constants
_CONST_4 = 4


class ServiceExtractor:
    """Extracts service names from Redis keyspace events"""

    def __init__(self):
        # Service name extraction pattern
        self._service_pattern = re.compile(r"^history:([^:]+)(?::|$)")

        # Known service names for validation
        self._known_services: Set[str] = {
            "deribit",
            "kalshi",
            "cfb",
            "weather",
            "cpu",
            "memory",
            "btc",
            "eth",
            "asos",
            "KAUS",
            "KMDW",
            "KORD",
            "KJFK",
            "KLAX",
            "KDEN",
            "KPHX",
        }

    def extract_service_name(self, redis_key: str) -> Optional[str]:
        """
        Extract service name from Redis key

        Args:
            redis_key: Redis key from keyspace event

        Returns:
            Service name if valid, None otherwise
        """
        match = self._service_pattern.match(redis_key)
        if not match:
            return None

        service_name = match.group(1)

        # For weather stations, normalize to 'weather'
        if len(service_name) == _CONST_4 and service_name.startswith("K"):
            return "weather"

        if service_name in self._known_services:
            return service_name

        logger.debug(f"Unknown service name from key {redis_key}: {service_name}")
        return None
