"""Field reset evaluation logic - slim coordinator."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .dawn_calculator import DawnCalculator
from .field_reset_evaluator_helpers import BoundaryChecker, EvaluationCases
from .timestamp_resolver import TimestampResolver

logger = logging.getLogger(__name__)


class FieldResetEvaluator:
    """
    Evaluates whether fields should be reset based on dawn boundaries.

    Slim coordinator delegating to specialized evaluation handlers.
    """

    def __init__(self, dawn_calculator: DawnCalculator, timestamp_resolver: TimestampResolver):
        """
        Initialize field reset evaluator.

        Args:
            dawn_calculator: Dawn calculator instance
            timestamp_resolver: Timestamp resolver instance
        """
        self.dawn_calculator = dawn_calculator
        self.timestamp_resolver = timestamp_resolver
        self._evaluation_cases = EvaluationCases(dawn_calculator)
        self._boundary_checker = BoundaryChecker()

    def should_reset_field(
        self,
        field_name: str,
        latitude: float,
        longitude: float,
        previous_data: Dict[str, Any],
        current_timestamp: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Check if a specific field should be reset due to local dawn crossing.

        Args:
            field_name: Name of the field to check
            latitude: Weather station latitude in decimal degrees
            longitude: Weather station longitude in decimal degrees
            previous_data: Previous data containing timestamps
            current_timestamp: Current timestamp (defaults to now UTC)

        Returns:
            Tuple of (should_reset, dawn_boundary)
        """
        if field_name not in self.timestamp_resolver.DAILY_RESET_FIELDS:
            return False, None

        from ..time_utils import get_current_utc

        if current_timestamp is None:
            current_timestamp = get_current_utc()

        last_dawn_reset = self.timestamp_resolver.get_last_dawn_reset_timestamp(previous_data)

        # Handle empty previous data (first run)
        if not previous_data:
            return self._evaluation_cases.evaluate_first_run(
                latitude, longitude, current_timestamp, last_dawn_reset, field_name
            )

        # Get the relevant timestamp from previous data
        timestamp_field = self.timestamp_resolver.get_timestamp_field_for_reset_field(field_name)
        if timestamp_field not in previous_data:
            return self._evaluation_cases.evaluate_missing_timestamp(
                latitude, longitude, current_timestamp, last_dawn_reset, field_name, timestamp_field
            )

        from .field_reset_evaluator_helpers.evaluation_cases import TimestampCrossingContext

        context = TimestampCrossingContext(
            latitude=latitude,
            longitude=longitude,
            current_timestamp=current_timestamp,
            last_dawn_reset=last_dawn_reset,
            field_name=field_name,
            timestamp_field=timestamp_field,
            previous_data=previous_data,
        )
        return self._evaluation_cases.evaluate_timestamp_crossing(context)
