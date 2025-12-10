"""Processes max temperature with confidence-based logic."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from common.exceptions import DataError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaxTempProcessingConfig:
    """Configuration for max temperature processing."""

    current_temp_c: float
    previous_data: Dict[str, Any]
    latitude: float
    longitude: float
    current_timestamp_str: str
    current_timestamp: Optional[datetime] = None
    six_hour_max_c: Optional[int] = None
    should_reset_override: Optional[bool] = None


class MaxTempProcessor:
    """Applies confidence-based max_temp_f logic using DailyMaxState."""

    def __init__(self, reset_evaluator):
        self._reset_evaluator = reset_evaluator

    def apply_confidence_based_max_temp_logic(
        self,
        config: MaxTempProcessingConfig,
    ):
        current_timestamp = config.current_timestamp
        if current_timestamp is None:
            from ..time_utils import get_current_utc

            current_timestamp = get_current_utc()

        from ..daily_max_state import create_daily_max_state

        daily_state = create_daily_max_state()
        should_reset = config.should_reset_override
        if should_reset is None:
            should_reset = self._reset_evaluator.should_reset_field(
                "max_temp_f",
                config.latitude,
                config.longitude,
                config.previous_data,
                current_timestamp,
            )

        if should_reset:
            logger.info("DAILY MAX RESET: Starting fresh daily max state (new local day)")
        else:
            logger.info("DAILY MAX CONTINUE: Restoring previous daily max state (same local day)")

        if not should_reset and "daily_max_state" in config.previous_data:
            try:
                state_dict = json.loads(config.previous_data["daily_max_state"])
                daily_state.load_from_state_dict(state_dict)
                logger.info("Successfully restored daily max state from previous data")
            except (json.JSONDecodeError, KeyError, ValueError):
                logger.exception("CRITICAL: Failed to restore daily max state from Redis data")
                stored_state = config.previous_data.get("daily_max_state")
                logger.exception("Corrupted daily_max_state data: %s", stored_state)
                raise ValueError("Cannot restore daily max state from corrupted Redis data")

        daily_state.add_hourly_observation(config.current_temp_c, current_timestamp)
        if config.six_hour_max_c is not None:
            daily_state.add_6h_maximum(config.six_hour_max_c, current_timestamp)

        result = daily_state.get_daily_max_result()
        if result is None:
            raise DataError("No temperature data available after adding current observation")

        max_temp_f = result.max_temp_f
        max_start_time = config.current_timestamp_str
        confidence = result.confidence
        logger.debug(
            "Daily max result: %s F (%s confidence, %s source)",
            max_temp_f,
            confidence,
            result.source,
        )
        return max_temp_f, max_start_time, confidence, daily_state
