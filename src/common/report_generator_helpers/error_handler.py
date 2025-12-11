"""Error handler for report generation operations.

Provides consistent error handling and logging for all report generation methods.
"""

import logging
from typing import Any, Awaitable, Callable, TypeVar

# Local constant for error handling
DATA_ACCESS_ERRORS = (KeyError, AttributeError, TypeError, ValueError)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ReportErrorHandler:
    """Handles errors for report generation with consistent logging."""

    @staticmethod
    async def handle_report_error(
        operation: Callable[..., Awaitable[T]],
        error_message: str,
        log_context: str,
        *args: Any,
        **kwargs: Any,
    ) -> T | str:
        """
        Execute a report generation operation with error handling.

        Args:
            operation: Async operation to execute
            error_message: User-facing error message prefix
            log_context: Context for logging
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result from operation or error message string

        Raises:
            Exception if operation raises non-data-access error
        """
        try:
            return await operation(*args, **kwargs)
        except DATA_ACCESS_ERRORS as exc:
            logger.error("Error in %s (%s): %s", log_context, type(exc).__name__, exc, exc_info=True)
            return f"❌ {error_message}"
