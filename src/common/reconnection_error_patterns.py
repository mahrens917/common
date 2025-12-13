"""
Reconnection error patterns for intelligent alert suppression.

This module defines error patterns that indicate routine reconnection events
rather than critical system failures, enabling intelligent suppression of
auxiliary monitoring alerts during normal connection recovery.
"""

import logging
from typing import Dict, List, Optional

from .reconnection_error_patterns_helpers.error_classifier import ErrorTypeClassifier
from .reconnection_error_patterns_helpers.error_matcher import ErrorMatcher
from .reconnection_error_patterns_helpers.pattern_compiler import (
    RECONNECTION_ERROR_PATTERNS,
    PatternCompiler,
)
from .reconnection_error_patterns_helpers.pattern_manager import PatternManager
from .reconnection_error_patterns_helpers.service_type_manager import (
    DEFAULT_SERVICE_TYPE_MAPPING,
    ServiceType,
    ServiceTypeManager,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ServiceType",
    "RECONNECTION_ERROR_PATTERNS",
    "DEFAULT_SERVICE_TYPE_MAPPING",
    "ReconnectionErrorClassifier",
    "get_error_classifier",
]


class ReconnectionErrorClassifier:
    """Classifier for identifying reconnection-related errors."""

    def __init__(self, service_type_mapping: Optional[Dict[str, ServiceType]] = None):
        """Initialize the error classifier."""
        self.service_type_manager = ServiceTypeManager(service_type_mapping)
        self.pattern_compiler = PatternCompiler()
        self.error_matcher = ErrorMatcher(self.pattern_compiler.compiled_patterns)
        self.error_type_classifier = ErrorTypeClassifier()
        self.pattern_manager = PatternManager(self.pattern_compiler)

        logger.debug(
            f"Initialized reconnection error classifier with " f"{len(self.service_type_manager.service_type_mapping)} service mappings"
        )

    def get_service_type(self, service_name: str) -> ServiceType:
        """Get the service type for a given service name."""
        return self.service_type_manager.get_service_type(service_name)

    def is_reconnection_error(self, service_name: str, error_message: str) -> bool:
        """Check if an error message indicates a reconnection event."""
        if not error_message:
            return False

        service_type = self.get_service_type(service_name)
        if service_type == ServiceType.UNKNOWN:
            logger.debug(f"Unknown service type for {service_name}, " "not classifying as reconnection error")
            return False

        return self.error_matcher.check_with_logging(service_name, service_type, error_message)

    def is_reconnection_error_by_type(self, service_type: str, error_message: str) -> bool:
        """Check if error indicates reconnection for specific service type."""
        if not error_message:
            return False

        service_type_enum = self.service_type_manager.string_to_service_type(service_type)
        if service_type_enum is None:
            logger.debug(f"Unknown service type: {service_type}")
            _none_guard_value = False
            return _none_guard_value

        matches, _ = self.error_matcher.matches_pattern(service_type_enum, error_message)
        if matches:
            logger.debug(f"Reconnection error detected for {service_type}: {error_message[:100]}...")
        return matches

    def classify_error_type(self, service_name: str, error_message: str) -> str:
        """Classify the type of error for detailed analysis."""
        return self.error_type_classifier.classify(error_message)

    def get_reconnection_patterns_for_service(self, service_name: str) -> List[str]:
        """Get all reconnection patterns for a specific service."""
        service_type = self.get_service_type(service_name)
        return self.pattern_manager.get_patterns_for_type(service_type)

    def add_service_type_mapping(self, service_name: str, service_type: ServiceType) -> None:
        """Add or update service type mapping."""
        self.service_type_manager.add_mapping(service_name, service_type)

    def add_custom_pattern(self, service_type: ServiceType, pattern: str) -> None:
        """Add a custom reconnection pattern for a service type."""
        self.pattern_manager.add_custom_pattern(service_type, pattern)


# Global classifier instance
_error_classifier: Optional[ReconnectionErrorClassifier] = None


def get_error_classifier() -> ReconnectionErrorClassifier:
    """
    Get the global error classifier instance.

    Returns:
        Initialized ReconnectionErrorClassifier instance
    """
    global _error_classifier

    if _error_classifier is None:
        _error_classifier = ReconnectionErrorClassifier()

    return _error_classifier
