"""Service name extraction utilities for MetadataInitializer."""

import re
from typing import Optional, Set

# Known service names
KNOWN_SERVICES: Set[str] = {
    "deribit",
    "kalshi",
    "cfb",
    "weather",
    "cpu",
    "memory",
    "btc",
    "eth",
    "asos",
    "metar",
    "KAUS",
    "KMDW",
    "KORD",
    "KJFK",
    "KLAX",
    "KDEN",
    "KPHX",
}


# Constants
_CONST_4 = 4


class ServiceNameExtractor:
    """Extracts service names from Redis keys."""

    def __init__(self):
        self._service_pattern = re.compile(r"^history:([^:]+)(?::|$)")

    def extract_service_name(self, redis_key: str) -> Optional[str]:
        """Extract service name from Redis key."""
        match = self._service_pattern.match(redis_key)
        if not match:
            return None

        service_name = match.group(1)

        # For weather stations, normalize to 'weather'
        if len(service_name) == _CONST_4 and service_name.startswith("K"):
            return "weather"

        if service_name in KNOWN_SERVICES:
            return service_name

        return None
