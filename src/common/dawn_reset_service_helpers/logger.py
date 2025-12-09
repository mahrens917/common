"""Logging helper for dawn reset service."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DawnCheckContext:
    """Context for dawn reset check logging."""

    latitude: float
    longitude: float
    previous_timestamp: datetime
    current_timestamp: datetime
    dawn_previous: datetime
    dawn_current: datetime
    dawn_reset_time: datetime
    is_new_day: bool
    relevant_dawn: Optional[datetime]
    is_cached: bool


class DawnResetLogger:
    """
    Handles detailed logging for dawn reset checks.

    Provides structured logging with caching awareness to avoid
    excessive log verbosity.
    """

    def log_dawn_check(
        self,
        context: DawnCheckContext,
    ) -> None:
        """
        Log dawn reset check results.

        Args:
            context: Dawn check context with all logging parameters
        """
        if context.is_cached:
            logger.debug(
                f"🌅 DAWN RESET CHECK (cached): lat={context.latitude:.4f}, lon={context.longitude:.4f}, new_day={context.is_new_day}"
            )
            return

        if context.is_new_day:
            logger.info(
                f"🌅 DAWN RESET CHECK: lat={context.latitude:.4f}, lon={context.longitude:.4f}"
            )
            logger.info(f"   Previous: {context.previous_timestamp.isoformat()}")
            logger.info(f"   Current:  {context.current_timestamp.isoformat()}")
            logger.info(f"   Dawn (previous day): {context.dawn_previous.isoformat()}")
            logger.info(f"   Dawn (current day):  {context.dawn_current.isoformat()}")
            logger.info(f"   Reset time (1 min before dawn): {context.dawn_reset_time.isoformat()}")
            logger.info(f"   ⏰ New trading day: {context.is_new_day}")

            if context.relevant_dawn:
                logger.info(
                    f"   ✅ Crossed dawn reset boundary: {context.relevant_dawn.isoformat()}"
                )
