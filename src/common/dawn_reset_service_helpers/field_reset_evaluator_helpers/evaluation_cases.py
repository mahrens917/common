"""Specific evaluation case handlers."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..dawn_calculator import DawnCalculator
from .boundary_checker import BoundaryChecker
from .evaluation_helpers import BoundaryEvaluator, TimestampCrossingEvaluator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimestampCrossingContext:
    """Context for timestamp crossing evaluation."""

    latitude: float
    longitude: float
    current_timestamp: datetime
    last_dawn_reset: Optional[datetime]
    field_name: str
    timestamp_field: str
    previous_data: Dict[str, Any]


class EvaluationCases:
    """Handles specific evaluation cases for field resets."""

    def __init__(self, dawn_calculator: DawnCalculator):
        checker = BoundaryChecker()
        self._boundary_evaluator = BoundaryEvaluator(dawn_calculator, checker)
        self._timestamp_evaluator = TimestampCrossingEvaluator(dawn_calculator, checker)

    def _boundary(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        message: str,
        context: str,
    ) -> Tuple[bool, Optional[datetime]]:
        return self._boundary_evaluator.evaluate_boundary(latitude, longitude, current_timestamp, last_dawn_reset, message, context)

    def evaluate_first_run(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        field_name: str,
    ) -> Tuple[bool, Optional[datetime]]:
        return self._boundary(
            latitude,
            longitude,
            current_timestamp,
            last_dawn_reset,
            f"🌅 FIRST RUN: No previous data for field '{field_name}' - new trading day (reset required)",
            "FIRST RUN",
        )

    def evaluate_missing_timestamp(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        field_name: str,
        timestamp_field: str,
    ) -> Tuple[bool, Optional[datetime]]:
        return self._boundary(
            latitude,
            longitude,
            current_timestamp,
            last_dawn_reset,
            f"🌅 MISSING TIMESTAMP: No '{timestamp_field}' for '{field_name}' - new trading day (reset required)",
            "MISSING TIMESTAMP",
        )

    def evaluate_null_timestamp(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        field_name: str,
        timestamp_field: str,
    ) -> Tuple[bool, Optional[datetime]]:
        return self._boundary(
            latitude,
            longitude,
            current_timestamp,
            last_dawn_reset,
            f"🌅 NULL TIMESTAMP: '{timestamp_field}' is None for '{field_name}' - new trading day (reset required)",
            "NULL TIMESTAMP",
        )

    def evaluate_timestamp_crossing(
        self,
        context: TimestampCrossingContext,
    ) -> Tuple[bool, Optional[datetime]]:
        previous_timestamp_raw = context.previous_data.get(context.timestamp_field)
        if previous_timestamp_raw is None:
            return self.evaluate_null_timestamp(
                context.latitude,
                context.longitude,
                context.current_timestamp,
                context.last_dawn_reset,
                context.field_name,
                context.timestamp_field,
            )
        return self._timestamp_evaluator.evaluate(
            context.latitude,
            context.longitude,
            context.current_timestamp,
            context.last_dawn_reset,
            context.field_name,
            previous_timestamp_raw,
        )
