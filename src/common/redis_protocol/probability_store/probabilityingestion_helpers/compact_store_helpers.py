# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""Helper functions for CompactStore."""

import logging
from typing import Any, Dict

from ...error_types import REDIS_ERRORS, SERIALIZATION_ERRORS
from ..exceptions import ProbabilityStoreError

# Constants extracted for ruff PLR2004 compliance
SAMPLE_LOGGED_5 = 5


logger = logging.getLogger(__name__)


async def execute_storage_pipeline(redis, pipeline, key: str, field_count: int, currency_upper: str):
    """Execute storage pipeline and validate results."""
    from ..pipeline import execute_pipeline

    results = await execute_pipeline(pipeline)
    expected_operations = 1 + field_count
    if len(results) != expected_operations:
        raise ProbabilityStoreError(f"Redis pipeline returned {len(results)} results; expected {expected_operations}")

    successful_sets = sum(int(bool(res)) for res in results[1:])
    if successful_sets != field_count:
        raise ProbabilityStoreError(
            "Redis stored {success} entries for {currency}; expected {expected}".format(
                success=successful_sets,
                currency=currency_upper,
                expected=field_count,
            )
        )

    actual_count = await redis.hlen(key)
    if actual_count != field_count:
        raise ProbabilityStoreError(
            "Field count mismatch after storing probabilities for {currency}: "
            "expected {expected}, got {actual}".format(
                currency=currency_upper,
                expected=field_count,
                actual=actual_count,
            )
        )


def log_sample_fields(field_iterator, probabilities_data: Dict[str, Dict[str, Dict[str, Any]]]):
    """Log sample probability fields for debugging."""
    sample_logged = 0
    for field, value, has_confidence, original in field_iterator.iter_probability_fields(probabilities_data):
        if sample_logged < 5:
            logger.info("ProbabilityStore adding field %s with data: %s", field, original)
            sample_logged += 1
        yield field, value, has_confidence


def handle_storage_errors(currency_upper: str):
    """Decorator to handle storage errors."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ValueError, TypeError, *SERIALIZATION_ERRORS) as exc:  # policy_guard: allow-silent-handler
                raise ProbabilityStoreError(f"Failed to store probabilities for {currency_upper}") from exc
            except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
                raise ProbabilityStoreError(f"Failed to store probabilities for {currency_upper}: Redis error {exc}") from exc

        return wrapper

    return decorator
