"""Record enqueuing logic for human-readable probability ingestion."""

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from ...probability_payloads import build_probability_record
from ..diagnostics import log_probability_diagnostics

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HumanReadableIngestionStats:
    """Statistics for human-readable probability ingestion."""

    field_count: int
    sample_keys: List[str]
    event_ticker_counts: Counter[str]


class RecordEnqueuer:
    """Handles enqueuing of probability records for pipeline execution."""

    def enqueue_human_readable_records(
        self,
        *,
        currency: str,
        probabilities_data: Dict[str, Dict[str, Dict[str, float]]],
        pipeline,
        sample_log_limit: int,
        verification_sample_limit: int,
    ) -> HumanReadableIngestionStats:
        """
        Enqueue human-readable probability records for pipeline execution.

        Args:
            currency: Currency code (e.g., "BTC")
            probabilities_data: Nested dict of expiry -> strike -> data
            pipeline: Redis pipeline
            sample_log_limit: Max number of samples to log
            verification_sample_limit: Max number of samples to verify

        Returns:
            Statistics about enqueued records
        """
        sample_log_count = 0
        field_count = 0
        sample_keys: List[str] = []
        event_ticker_counts: Counter[str] = Counter()

        for expiry, strikes_data in probabilities_data.items():
            for strike_val, raw_data in strikes_data.items():
                record = build_probability_record(
                    currency,
                    expiry,
                    strike_val,
                    raw_data,
                    default_missing_event_ticker=True,
                )

                if not record.fields:
                    logger.debug("Skipping probability key %s due to empty payload", record.key)
                    continue

                if sample_log_count < sample_log_limit:
                    logger.info(
                        "ProbabilityStore storing key %s with payload %s",
                        record.key,
                        raw_data,
                    )
                    sample_log_count += 1

                log_probability_diagnostics(record)
                pipeline.hset(record.key, mapping=record.fields)
                field_count += 1

                if len(sample_keys) < verification_sample_limit:
                    sample_keys.append(record.key)

                if record.event_ticker:
                    event_ticker_counts[record.event_ticker] += 1

        return HumanReadableIngestionStats(
            field_count=field_count,
            sample_keys=sample_keys,
            event_ticker_counts=event_ticker_counts,
        )
