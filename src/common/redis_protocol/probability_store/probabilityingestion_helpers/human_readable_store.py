"""Human-readable format probability storage."""

import logging
from typing import Awaitable, Callable, Dict

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ..diagnostics import log_event_ticker_summary
from ..exceptions import ProbabilityStoreError
from ..pipeline import create_pipeline, execute_pipeline
from ..verification import verify_probability_storage
from .key_collector import KeyCollector
from .record_enqueuer import RecordEnqueuer

logger = logging.getLogger(__name__)


class HumanReadableStore:
    """Handles storage of probabilities in human-readable format."""

    def __init__(
        self,
        redis_provider: Callable[[], Awaitable[Redis]],
        key_collector: KeyCollector,
        record_enqueuer: RecordEnqueuer,
    ) -> None:
        self._redis_provider = redis_provider
        self._key_collector = key_collector
        self._record_enqueuer = record_enqueuer

    async def store_probabilities_human_readable(self, currency: str, probabilities_data: Dict[str, Dict[str, Dict[str, float]]]) -> bool:
        currency_upper = currency.upper()
        logger.info("Storing human-readable probabilities for %s", currency_upper)
        logger.info(
            "Data contains %s expiries with %s total strikes",
            len(probabilities_data),
            sum(len(strikes) for strikes in probabilities_data.values()),
        )

        redis = await self._redis_provider()
        pipeline = await create_pipeline(redis)

        prefix = f"probabilities:{currency_upper}:"
        keys_to_delete = await self._key_collector.collect_existing_probability_keys(redis, prefix)
        if keys_to_delete:
            logger.info("Deleting %s existing keys with prefix %s", len(keys_to_delete), prefix)
            self._key_collector.queue_probability_deletes(pipeline, keys_to_delete)

        try:
            stats = self._record_enqueuer.enqueue_human_readable_records(
                currency=currency_upper,
                probabilities_data=probabilities_data,
                pipeline=pipeline,
                sample_log_limit=5,
                verification_sample_limit=4,
            )
            logger.info(
                "Executing Redis pipeline with %s hash updates for human-readable probabilities",
                stats.field_count,
            )
            results = await execute_pipeline(pipeline)

            expected_operations = len(keys_to_delete) + stats.field_count
        except (
            ValueError,
            TypeError,
            ProbabilityStoreError,
        ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            await self._handle_ingestion_failure(redis, currency_upper, probabilities_data, exc)
        except REDIS_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
            await self._handle_ingestion_failure(redis, currency_upper, probabilities_data, exc)
        else:
            if len(results) != expected_operations:
                exc = ProbabilityStoreError(f"Redis pipeline returned {len(results)} results; expected {expected_operations}")
                await self._handle_ingestion_failure(redis, currency_upper, probabilities_data, exc)
            else:
                await verify_probability_storage(redis, stats.sample_keys, currency_upper)
                log_event_ticker_summary(currency_upper, stats.field_count, stats.event_ticker_counts)
                return True
        return False

    async def _handle_ingestion_failure(
        self,
        redis: Redis,
        currency: str,
        probabilities_data: Dict[str, Dict[str, Dict[str, float]]],
        exc: BaseException,
    ) -> None:
        from ..diagnostics import log_failure_context
        from ..verification import run_direct_connectivity_test

        log_failure_context(probabilities_data)
        await run_direct_connectivity_test(redis, currency)
        raise ProbabilityStoreError(f"Failed to store human-readable probabilities for {currency}") from exc
