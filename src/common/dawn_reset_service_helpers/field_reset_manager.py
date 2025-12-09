"""Field reset evaluation and application - slim coordinator."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from .dawn_calculator import DawnCalculator
from .field_reset_applicator import FieldResetApplicator
from .field_reset_evaluator import FieldResetEvaluator
from .timestamp_resolver import TimestampResolver

logger = logging.getLogger(__name__)


class FieldResetManager:
    """
    Evaluates if fields should be reset and applies reset logic.

    Slim coordinator delegating to specialized evaluator and applicator.
    """

    CLEAR_ON_RESET_FIELDS = FieldResetApplicator.CLEAR_ON_RESET_FIELDS

    def __init__(self, dawn_calculator: DawnCalculator, timestamp_resolver: TimestampResolver):
        """
        Initialize field reset manager.

        Args:
            dawn_calculator: Dawn calculator instance
            timestamp_resolver: Timestamp resolver instance
        """
        self.dawn_calculator = dawn_calculator
        self.timestamp_resolver = timestamp_resolver
        self._evaluator = FieldResetEvaluator(dawn_calculator, timestamp_resolver)
        self._applicator = FieldResetApplicator()

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
        return self._evaluator.should_reset_field(
            field_name, latitude, longitude, previous_data, current_timestamp
        )

    def apply_reset_logic(
        self, field_name: str, current_value: Any, previous_data: Dict[str, Any], was_reset: bool
    ) -> Any:
        """
        Apply reset logic to a field value.

        Args:
            field_name: Name of the field
            current_value: Current value for the field
            previous_data: Previous data to check against
            was_reset: Whether reset is needed

        Returns:
            Final value after applying reset logic
        """
        return self._applicator.apply_reset_logic(
            field_name, current_value, previous_data, was_reset
        )
