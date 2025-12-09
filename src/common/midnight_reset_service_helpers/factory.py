"""Factory for creating MidnightResetService with wired dependencies."""

from .daily_checker import DailyChecker
from .delegator import MidnightResetDelegator
from .field_reset_applicator import FieldResetApplicator
from .max_temp_processor import MaxTempProcessor
from .reset_evaluator import ResetEvaluator
from .timestamp_mapper import TimestampMapper


def create_midnight_reset_service() -> MidnightResetDelegator:
    """
    Create a fully wired MidnightResetService instance.

    Returns:
        MidnightResetDelegator with all dependencies wired
    """
    # Create helper instances
    daily_checker = DailyChecker()
    timestamp_mapper = TimestampMapper()
    reset_evaluator = ResetEvaluator(daily_checker, timestamp_mapper)
    field_reset_applicator = FieldResetApplicator(reset_evaluator)
    max_temp_processor = MaxTempProcessor(reset_evaluator)

    # Create and return delegator
    return MidnightResetDelegator(
        daily_checker=daily_checker,
        timestamp_mapper=timestamp_mapper,
        reset_evaluator=reset_evaluator,
        field_reset_applicator=field_reset_applicator,
        max_temp_processor=max_temp_processor,
    )
