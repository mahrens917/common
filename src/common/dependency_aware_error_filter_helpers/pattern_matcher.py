"""Error pattern matching logic."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PatternCompilationError(ValueError):
    """Raised when a regex pattern fails to compile."""


@dataclass
class DependencyErrorPattern:
    """Configuration for dependency-related error patterns"""

    dependency_name: str
    error_patterns: List[str]
    compiled_patterns: Optional[List[re.Pattern]] = None

    def __post_init__(self) -> None:
        """Compile regex patterns for performance.

        Raises:
            PatternCompilationError: If any pattern fails to compile
        """
        if self.error_patterns and not self.compiled_patterns:
            self.compiled_patterns = []
            for pattern in self.error_patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self.compiled_patterns.append(compiled)
                except re.error:
                    logger.exception(
                        "Invalid regex pattern '%s' for dependency %s",
                        pattern,
                        self.dependency_name,
                    )


class PatternMatcher:
    """Matches error messages against dependency patterns."""

    @staticmethod
    def is_dependency_related_error(error_message: str, dependency_name: str, dependency_patterns: Dict) -> bool:
        """Check if an error message is related to a specific dependency."""
        if dependency_name not in dependency_patterns:
            return False

        pattern_config = dependency_patterns[dependency_name]
        compiled_patterns = pattern_config.compiled_patterns or []
        if not compiled_patterns:
            return False

        for pattern in compiled_patterns:
            try:
                if pattern.search(error_message):
                    logger.debug("Error message matches %s pattern: %s", dependency_name, pattern.pattern)
                    return True
            except re.error as exc:
                logger.warning(
                    "Error matching pattern %s: %s",
                    getattr(pattern, "pattern", "<pattern>"),
                    exc,
                )

        return False
