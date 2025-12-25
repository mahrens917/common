"""Compact format probability storage."""

import logging
from typing import Any, Awaitable, Callable, Dict

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS, SERIALIZATION_ERRORS
from ..exceptions import ProbabilityStoreError
from ..pipeline import create_pipeline, execute_pipeline
from .field_iterator import FieldIterator

logger = logging.getLogger(__name__)


# Constants
_CONST_5 = 5


class CompactStore:
    """Handles storage of probabilities in compact format."""

    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[Redis]],
        field_iterator: FieldIterator,
    ) -> None:
        self._redis_provider = redis_provider
        self._field_iterator = field_iterator

    async def store_probabilities(self, currency: str, probabilities_data: Dict[str, Dict[str, Dict[str, Any]]]) -> bool:
        """
        Store probabilities in compact format.

        Args:
            currency: Currency code (e.g., "BTC")
            probabilities_data: Nested dict of expiry -> strike -> data

        Returns:
            True if storage successful

        Raises:
            ProbabilityStoreError: If storage fails
        """
        currency_upper = currency.upper()
        key = f"probabilities:{currency_upper}"

        try:
            redis = await self._redis_provider()
            pipeline = await create_pipeline(redis)
            pipeline.delete(key)

            stats = _enqueue_probability_fields(
                pipeline,
                key,
                self._field_iterator.iter_probability_fields(probabilities_data),
            )

            results = await execute_pipeline(pipeline)
            _validate_pipeline_results(results, stats["field_count"], currency_upper)
            await _validate_stored_field_count(redis, key, stats["field_count"], currency_upper)
            _log_store_summary(stats, currency_upper)
        except (ValueError, TypeError, *SERIALIZATION_ERRORS) as exc:
            raise ProbabilityStoreError(f"Failed to store probabilities for {currency_upper}") from exc
        except REDIS_ERRORS as exc:
            raise ProbabilityStoreError(f"Failed to store probabilities for {currency_upper}: Redis error {exc}") from exc
        else:
            return True


def _enqueue_probability_fields(pipeline, key: str, field_iterator):
    field_count = 0
    confidence_count = 0
    sample_logged = 0

    for field, value, has_confidence, original in field_iterator:
        if sample_logged < _CONST_5:
            logger.info("ProbabilityStore adding field %s with data: %s", field, original)
            sample_logged += 1
        if has_confidence:
            confidence_count += 1
        pipeline.hset(key, field, value)
        field_count += 1

    return {"field_count": field_count, "confidence_count": confidence_count}


def _validate_pipeline_results(results, field_count: int, currency_upper: str) -> None:
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


async def _validate_stored_field_count(redis, key: str, field_count: int, currency_upper: str):
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


def _log_store_summary(stats: Dict[str, int], currency_upper: str) -> None:
    logger.info(
        "Stored %s probability fields for %s (confidence entries=%s)",
        stats["field_count"],
        currency_upper,
        stats["confidence_count"],
    )
