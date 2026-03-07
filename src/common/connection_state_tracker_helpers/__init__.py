"""Connection State Tracker Helper Components."""

import asyncio
import logging
from json import JSONDecodeError

from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

STORE_ERROR_TYPES = (
    ConnectionError,
    RedisError,
    RuntimeError,
    asyncio.TimeoutError,
    JSONDecodeError,
)


class ConnectionStateTrackerError(RuntimeError):
    """Raised when connection state persistence fails."""


def build_tracker_error(message: str, error: Exception) -> ConnectionStateTrackerError:
    """Log failure context and return a tracker-specific error."""
    logger.exception("%s: %s", message, error, exc_info=True)
    new_error = ConnectionStateTrackerError(message)
    new_error.__cause__ = error
    return new_error
