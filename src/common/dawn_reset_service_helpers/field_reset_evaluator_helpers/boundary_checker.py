"""Dawn boundary processing logic."""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _format_timestamp(value: Optional[datetime]) -> str:
    if value is None:
        return "<missing>"
    return value.isoformat()


def format_timestamp(value: Optional[datetime]) -> str:
    """Public alias that reuses the internal formatter."""
    return _format_timestamp(value)


class BoundaryChecker:
    """Checks if dawn boundaries have been processed."""

    @staticmethod
    def already_processed(last_dawn_reset: Optional[datetime], boundary: Optional[datetime]) -> bool:
        """Check if boundary was already processed."""
        if boundary is None:
            return False
        if last_dawn_reset is None:
            return False
        return last_dawn_reset >= boundary

    @staticmethod
    def log_skip(last_dawn_reset: Optional[datetime], boundary: Optional[datetime], context: str) -> None:
        """Log that a boundary was skipped."""
        logger.debug(
            "🌅 %s SKIP: Stored dawn reset at %s covers boundary %s",
            context,
            format_timestamp(last_dawn_reset),
            format_timestamp(boundary),
        )
