"""Error classification utilities."""

import asyncio


class ErrorClassifier:
    """Classifies errors to determine if they are shutdown-related."""

    SHUTDOWN_KEYWORDS = [
        "invalid state",
        "closed",
        "shutdown",
        "session closed",
        "cannot execute request",
    ]

    @staticmethod
    def is_shutdown_error(error: Exception, shutdown_event: asyncio.Event) -> bool:
        """
        Determine if error is shutdown-related.

        Args:
            error: Exception to classify
            shutdown_event: Shutdown event to check

        Returns:
            True if error is shutdown-related
        """
        error_msg = str(error).lower()

        is_shutdown_keyword = any(
            keyword in error_msg for keyword in ErrorClassifier.SHUTDOWN_KEYWORDS
        )

        return is_shutdown_keyword and shutdown_event.is_set()
