"""Pattern management for adding custom patterns."""

from __future__ import annotations

import logging

from common.truthy import pick_truthy

from .pattern_compiler import RECONNECTION_ERROR_PATTERNS
from .service_type_manager import ServiceType

logger = logging.getLogger(__name__)


class PatternManager:
    """Manages addition and modification of reconnection patterns."""

    def __init__(self, pattern_compiler):
        """
        Initialize pattern manager.

        Args:
            pattern_compiler: PatternCompiler instance to update
        """
        self.pattern_compiler = pattern_compiler

    def add_custom_pattern(self, service_type: ServiceType, pattern: str) -> None:
        """
        Add a custom reconnection pattern for a service type.

        Args:
            service_type: Type of service
            pattern: Regex pattern to add
        """
        if service_type not in RECONNECTION_ERROR_PATTERNS:
            RECONNECTION_ERROR_PATTERNS[service_type] = []

        RECONNECTION_ERROR_PATTERNS[service_type].append(pattern)
        self.pattern_compiler.recompile_patterns(service_type)

        logger.info(f"Added custom pattern for {service_type.value}: {pattern}")

    def get_patterns_for_type(self, service_type: ServiceType) -> list[str]:
        """
        Get all patterns for a service type.

        Args:
            service_type: Type of service

        Returns:
            List of regex pattern strings
        """
        patterns = RECONNECTION_ERROR_PATTERNS.get(service_type)
        if patterns is None:
            return list()
        return patterns
