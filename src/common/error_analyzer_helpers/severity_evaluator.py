"""Severity evaluation for errors."""

import logging
from typing import Any, Dict, Optional

from .data_classes import ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class SeverityEvaluator:
    """Evaluates error severity based on category and context."""

    def determine_severity(
        self, error: Exception, category: ErrorCategory, context: Optional[Dict[str, Any]]
    ) -> ErrorSeverity:
        """Determine error severity."""
        # Critical errors that require immediate attention
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.CRITICAL

        # High severity for core functionality
        if category in [ErrorCategory.DEPENDENCY, ErrorCategory.WEBSOCKET]:
            return ErrorSeverity.HIGH

        # Medium severity for recoverable issues
        if category in [ErrorCategory.NETWORK, ErrorCategory.API]:
            return ErrorSeverity.MEDIUM

        # Low severity for data/resource issues
        return ErrorSeverity.LOW
