"""Observation tracking logic for daily maximum temperatures."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from common.truthy import pick_if, pick_truthy

logger = logging.getLogger(__name__)


class ObservationTracker:
    """Tracks hourly and 6-hour temperature observations."""

    @staticmethod
    def add_hourly_observation(state: Dict[str, Any], temp_c: Optional[float], timestamp: Optional[datetime] = None) -> None:
        """
        Add 1-hour temperature observation with 0.1°C precision.

        Args:
            state: State dictionary to update
            temp_c: Temperature in Celsius with 0.1°C precision
            timestamp: When this temperature was observed

        Raises:
            ValueError: If temperature is None or invalid
        """
        if temp_c is None:
            raise ValueError("Temperature cannot be None")

        if timestamp is None:
            from ..time_utils import get_current_utc

            timestamp = get_current_utc()

        # Update overall daily maximum
        if temp_c > state["max_temp_c"]:
            state["max_temp_c"] = temp_c
            state["precision"] = 0.1
            state["source"] = "hourly"
            state["timestamp"] = timestamp

            logger.debug(f"New daily max from hourly: {temp_c}°C (HIGH confidence)")

        # Update hourly-only maximum for Rule 4
        if temp_c > state["hourly_max_temp_c"]:
            state["hourly_max_temp_c"] = temp_c
            state["hourly_timestamp"] = timestamp
            logger.debug(f"New hourly-only max: {temp_c}°C for Rule 4")

    @staticmethod
    def add_6h_maximum(
        state: Dict[str, Any],
        metar_config: Dict[str, Any],
        max_c: Optional[int],
        window_end: Optional[datetime] = None,
    ) -> None:
        """
        Add 6-hour maximum temperature as integer °C.
        Applies configurable safety margin for conservative estimates.

        Args:
            state: State dictionary to update
            metar_config: METAR configuration containing safety margins
            max_c: Maximum temperature over 6-hour window as integer °C
            window_end: End of the 6-hour window

        Raises:
            ValueError: If temperature is None or invalid
        """
        if max_c is None:
            raise ValueError("6-hour maximum cannot be None")

        if window_end is None:
            from ..time_utils import get_current_utc

            window_end = get_current_utc()

        # Apply safety margin from config for 6-hour data (less precise)
        six_h_config = pick_truthy(metar_config.get("6h_max"), {})
        safety_margin_value = six_h_config.get("safety_margin_celsius") if isinstance(six_h_config, dict) else None
        safety_margin = 0.5
        if safety_margin_value is not None:
            try:
                safety_margin = float(safety_margin_value)
            except (TypeError, ValueError):  # policy_guard: allow-silent-handler
                safety_margin = 0.5
        max_c_float = float(max_c) - safety_margin

        # Only update overall daily maximum (NOT hourly-only max)
        if max_c_float > state["max_temp_c"]:
            state["max_temp_c"] = max_c_float
            state["precision"] = 1.0
            state["source"] = "6h"
            state["timestamp"] = window_end

            logger.debug(f"New daily max from 6h: {max_c}°C -> {max_c_float}°C (MEDIUM confidence)")
