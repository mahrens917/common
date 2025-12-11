"""Service type mapping management."""

import logging
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """
    Service types for categorizing error patterns.

    Different service types have different connection patterns and error signatures,
    requiring tailored error pattern matching for accurate reconnection detection.
    """

    WEBSOCKET = "websocket"
    REST = "rest"
    DATABASE = "database"
    SCRAPER = "scraper"
    UNKNOWN = "unknown"


# Service name to service type mapping
DEFAULT_SERVICE_TYPE_MAPPING: Dict[str, ServiceType] = {
    "deribit": ServiceType.WEBSOCKET,
    "kalshi": ServiceType.WEBSOCKET,
    "cfb": ServiceType.SCRAPER,
    "weather": ServiceType.REST,
    "tracker": ServiceType.REST,
}


class ServiceTypeManager:
    """Manages service type mappings."""

    def __init__(self, custom_mapping: Dict[str, ServiceType] | None = None):
        """
        Initialize service type manager.

        Args:
            custom_mapping: Optional custom mapping of service names to types
        """
        self.service_type_mapping = custom_mapping or DEFAULT_SERVICE_TYPE_MAPPING.copy()
        logger.debug(f"Initialized service type manager with {len(self.service_type_mapping)} mappings")

    def get_service_type(self, service_name: str) -> ServiceType:
        """
        Get the service type for a given service name.

        Args:
            service_name: Name of the service

        Returns:
            ServiceType for the service
        """
        return self.service_type_mapping.get(service_name, ServiceType.UNKNOWN)

    def add_mapping(self, service_name: str, service_type: ServiceType) -> None:
        """
        Add or update service type mapping.

        Args:
            service_name: Name of the service
            service_type: Type of the service
        """
        self.service_type_mapping[service_name] = service_type
        logger.info(f"Added service type mapping: {service_name} -> {service_type.value}")

    def string_to_service_type(self, service_type_str: str) -> ServiceType | None:
        """
        Convert string service type to ServiceType enum.

        Args:
            service_type_str: String representation of service type

        Returns:
            ServiceType enum or None if unknown
        """
        mapping = {
            "websocket": ServiceType.WEBSOCKET,
            "rest": ServiceType.REST,
            "scraper": ServiceType.SCRAPER,
            "database": ServiceType.DATABASE,
        }
        return mapping.get(service_type_str.lower())
