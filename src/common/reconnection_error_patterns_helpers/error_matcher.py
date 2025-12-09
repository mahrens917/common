"""Error message matching against reconnection patterns."""

import logging
import re
from typing import List

from .service_type_manager import ServiceType

logger = logging.getLogger(__name__)


class ErrorMatcher:
    """Matches error messages against reconnection patterns."""

    def __init__(self, compiled_patterns: dict[ServiceType, List[re.Pattern]]):
        """
        Initialize error matcher.

        Args:
            compiled_patterns: Dictionary of compiled regex patterns by service type
        """
        self.compiled_patterns = compiled_patterns

    def matches_pattern(
        self, service_type: ServiceType, error_message: str
    ) -> tuple[bool, str | None]:
        """
        Check if error message matches any reconnection pattern.

        Args:
            service_type: Type of service
            error_message: Error message to check

        Returns:
            Tuple of (matches, matched_pattern_string)
        """
        if not error_message:
            return False, None

        if service_type == ServiceType.UNKNOWN:
            return False, None

        patterns = self.compiled_patterns.get(service_type) or []

        for pattern in patterns:
            if pattern.search(error_message):
                return True, pattern.pattern

        return False, None

    def check_with_logging(
        self, service_name: str, service_type: ServiceType, error_message: str
    ) -> bool:
        """
        Check pattern match with debug logging.

        Args:
            service_name: Name of the service
            service_type: Type of service
            error_message: Error message to check

        Returns:
            True if matches reconnection pattern
        """
        matches, pattern = self.matches_pattern(service_type, error_message)

        if matches:
            logger.debug(
                f"Reconnection error detected for {service_name}: "
                f"{error_message[:100]}... (pattern: {pattern})"
            )
        else:
            logger.debug(
                f"No reconnection pattern match for {service_name}: {error_message[:100]}..."
            )

        return matches
