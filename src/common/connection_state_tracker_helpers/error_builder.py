"""Error building utilities for ConnectionStateTracker."""

import logging

logger = logging.getLogger(__name__)


class ConnectionStateTrackerError(RuntimeError):
    """Raised when connection state persistence fails."""


def build_tracker_error(message: str, error: Exception) -> ConnectionStateTrackerError:
    """Log failure context and return a tracker-specific error."""
    logger.exception("%s: %s", message, error, exc_info=True)
    new_error = ConnectionStateTrackerError(message)
    new_error.__cause__ = error
    return new_error
