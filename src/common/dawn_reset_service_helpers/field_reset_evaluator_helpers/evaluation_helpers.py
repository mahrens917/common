"""Helper functions for evaluation cases."""

from datetime import datetime
from typing import Optional, Tuple

from common.exceptions import DataError

from .boundary_checker import BoundaryChecker, format_timestamp
from .dawn_calculator import DawnCalculator


class _BaseEvaluator:
    """Shared dependency wiring for dawn reset evaluators."""

    def __init__(self, dawn_calculator: DawnCalculator, boundary_checker: BoundaryChecker):
        self.dawn_calculator = dawn_calculator
        self.boundary_checker = boundary_checker


class BoundaryEvaluator(_BaseEvaluator):
    """Handles boundary evaluation logic."""

    def evaluate_boundary(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        log_msg: str,
        context: str,
    ) -> Tuple[bool, Optional[datetime]]:
        """Common boundary check logic."""
        import logging

        logger = logging.getLogger(__name__)
        boundary = self.dawn_calculator.resolve_latest_dawn_boundary(latitude, longitude, current_timestamp)
        if self.boundary_checker.already_processed(last_dawn_reset, boundary):
            self.boundary_checker.log_skip(last_dawn_reset, boundary, context)
            return False, boundary
        logger.info(log_msg)
        return True, boundary


class TimestampCrossingEvaluator(_BaseEvaluator):
    """Handles timestamp crossing evaluation."""

    def evaluate(
        self,
        latitude: float,
        longitude: float,
        current_timestamp: datetime,
        last_dawn_reset: Optional[datetime],
        field_name: str,
        previous_timestamp_raw: Optional[str],
    ) -> Tuple[bool, Optional[datetime]]:
        """Evaluate reset based on timestamp crossing."""
        import logging

        logger = logging.getLogger(__name__)

        if previous_timestamp_raw is None:
            return False, None

        try:
            previous_timestamp = datetime.fromisoformat(previous_timestamp_raw.replace("Z", "+00:00"))
            is_new_day, boundary = self.dawn_calculator.is_new_trading_day(latitude, longitude, previous_timestamp, current_timestamp)
            if not is_new_day:
                return False, None

            if self.boundary_checker.already_processed(last_dawn_reset, boundary):
                logger.info(
                    "🌅 DAWN RESET SKIP: Last processed dawn at %s already covers boundary %s for field '%s'",
                    format_timestamp(last_dawn_reset),
                    format_timestamp(boundary),
                    field_name,
                )
                return False, boundary

            else:
                return True, boundary
        except (ValueError, AttributeError, KeyError) as exc:  # policy_guard: allow-silent-handler
            logger.error(
                f"Failed to parse timestamp '{previous_timestamp_raw}' for field '{field_name}'",
                exc_info=True,
            )
            raise DataError(f"Failed to parse timestamp '{previous_timestamp_raw}' for field '{field_name}'") from exc
