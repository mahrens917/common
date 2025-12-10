"""Helper functions for max temperature processing."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from common.exceptions import DataError

logger = logging.getLogger(__name__)


def initialize_or_restore_daily_state(should_reset: bool, previous_data: Dict[str, Any]):
    """Initialize or restore daily max state based on reset condition."""
    from ..daily_max_state import create_daily_max_state

    daily_state: Any = create_daily_max_state()

    if should_reset:
        logger.info("< DAILY MAX RESET: Starting fresh daily max state (new local day)")
        return daily_state

    logger.info("= DAILY MAX CONTINUE: Restoring previous daily max state (same local day)")

    if "daily_max_state" in previous_data:
        try:
            state_dict = json.loads(previous_data["daily_max_state"])
            persistence = getattr(daily_state, "persistence", None)
            if hasattr(daily_state, "load_from_state_dict"):
                daily_state.load_from_state_dict(state_dict)
            elif persistence is not None and hasattr(persistence, "load_from_state_dict"):
                persistence.load_from_state_dict(state_dict)
            else:
                daily_state.__dict__["state"] = state_dict
            logger.info(" Successfully restored daily max state from previous data")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            _stored_state = previous_data.get("daily_max_state", "MISSING")
            logger.exception("CRITICAL: Failed to restore daily max state from Redis data")
            logger.exception("Corrupted daily_max_state data")
            raise DataError(f"Cannot restore daily max state from corrupted Redis data") from exc

    return daily_state


def add_observations_to_state(
    daily_state, current_temp_c: float, current_timestamp: datetime, six_hour_max_c: Optional[int]
):
    """Add current observations to daily state."""
    daily_state.add_hourly_observation(current_temp_c, current_timestamp)
    if six_hour_max_c is not None:
        daily_state.add_6h_maximum(six_hour_max_c, current_timestamp)


def extract_result_for_trading(daily_state, current_timestamp_str: str):
    """Extract daily max result for trading decisions."""
    result = daily_state.get_daily_max_result()

    if result is None:
        raise DataError("No temperature data available after adding current observation")

    max_temp_f = result.max_temp_f
    max_start_time = current_timestamp_str
    confidence = result.confidence

    logger.debug(
        "Daily max result: %sF (%s confidence, %s source)",
        max_temp_f,
        confidence,
        result.source,
    )

    return max_temp_f, max_start_time, confidence
