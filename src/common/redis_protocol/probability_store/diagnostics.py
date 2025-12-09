from __future__ import annotations

"""Logging helpers for the probability store."""


import logging
from collections import Counter
from typing import Dict, Mapping, Union

from ..probability_payloads import ProbabilityRecord

logger = logging.getLogger(__name__)


def log_probability_diagnostics(record: ProbabilityRecord) -> None:
    diagnostics = record.diagnostics
    if diagnostics.error_value is None:
        logger.debug("No error value provided for key %s", record.key)
    else:
        logger.debug(
            "Error value for key %s -> %s (stored=%s)",
            record.key,
            diagnostics.error_value,
            diagnostics.stored_error,
        )

    if diagnostics.confidence_value is None:
        logger.debug("No confidence value provided for key %s", record.key)
    else:
        logger.debug(
            "Confidence value for key %s -> %s (stored=%s)",
            record.key,
            diagnostics.confidence_value,
            diagnostics.stored_confidence,
        )


def log_human_readable_summary(
    currency: str,
    key_count: int,
    result: Mapping[str, Mapping[str, Mapping[str, Mapping[str, Union[str, float]]]]],
) -> None:
    expiry_count = len(result)
    event_title_count = sum(len(event_titles) for event_titles in result.values())
    total_strikes = sum(
        len(strikes)
        for event_titles in result.values()
        for strike_types in event_titles.values()
        for strikes in strike_types.values()
    )
    logger.debug(
        "Processed %s keys into %s expiries with %s event titles and %s total strikes for %s",
        key_count,
        expiry_count,
        event_title_count,
        total_strikes,
        currency,
    )


def log_event_type_summary(
    currency: str,
    event_type: str,
    key_count: int,
    result: Mapping[str, Mapping[str, Mapping[str, Mapping[str, Union[str, float]]]]],
) -> None:
    expiry_count = len(result)
    total_strikes = sum(
        len(strikes) for strike_types in result.values() for strikes in strike_types.values()
    )
    logger.info(
        "Retrieved %s probability keys for event type '%s' for %s",
        key_count,
        event_type,
        currency,
    )
    logger.info("Processed into %s expiries with %s total strikes", expiry_count, total_strikes)


def log_event_ticker_summary(
    currency: str, field_count: int, event_ticker_counts: Counter[str]
) -> None:
    event_ticker_count = len(event_ticker_counts)
    logger.info(
        "Stored %s human-readable probability entries for %s across %s event tickers",
        field_count,
        currency,
        event_ticker_count,
    )
    for event_ticker, count in event_ticker_counts.most_common(10):
        logger.info("  Event ticker '%s': %s entries", event_ticker, count)


def log_failure_context(probabilities_data: Dict[str, Dict[str, Dict[str, float]]]) -> None:
    logger.error("  - probabilities_data contains %s expiries", len(probabilities_data))
    if not probabilities_data:
        return

    sample_expiry = next(iter(probabilities_data))
    logger.error(
        "  - Sample expiry %s has %s strike entries",
        sample_expiry,
        len(probabilities_data[sample_expiry]),
    )


__all__ = [
    "log_probability_diagnostics",
    "log_human_readable_summary",
    "log_event_type_summary",
    "log_event_ticker_summary",
    "log_failure_context",
]
