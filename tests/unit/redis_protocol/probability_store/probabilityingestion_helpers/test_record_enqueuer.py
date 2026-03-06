"""Unit tests for RecordEnqueuer."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer import (
    HumanReadableIngestionStats,
    RecordEnqueuer,
)


class _FakePipeline:
    def __init__(self):
        self.calls = []

    def hset(self, key, mapping):
        self.calls.append((key, mapping))


def _make_record(key="k1", fields=None, event_ticker="ev1"):
    from common.redis_protocol.probability_payloads import ProbabilityFieldDiagnostics, ProbabilityRecord

    diag = ProbabilityFieldDiagnostics(error_value=None, stored_error=False, confidence_value=None, stored_confidence=False)
    if fields is None:
        fields = {"probability": "0.5"}
    return ProbabilityRecord(key=key, fields=fields, event_ticker=event_ticker, diagnostics=diag)


class TestRecordEnqueuer:
    """Tests for RecordEnqueuer.enqueue_human_readable_records."""

    def test_enqueues_records(self) -> None:
        enqueuer = RecordEnqueuer()
        pipeline = _FakePipeline()

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.build_probability_record",
                return_value=_make_record(),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.log_probability_diagnostics",
            ),
        ):
            stats = enqueuer.enqueue_human_readable_records(
                currency="BTC",
                probabilities_data={"2025-01-01": {"50000": {"probability": 0.5}}},
                pipeline=pipeline,
                sample_log_limit=5,
                verification_sample_limit=5,
            )

        assert isinstance(stats, HumanReadableIngestionStats)
        assert stats.field_count == 1
        assert "k1" in stats.sample_keys
        assert stats.event_ticker_counts["ev1"] == 1

    def test_skips_empty_fields(self) -> None:
        enqueuer = RecordEnqueuer()
        pipeline = _FakePipeline()

        empty_record = _make_record(fields={})

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.build_probability_record",
                return_value=empty_record,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.log_probability_diagnostics",
            ),
        ):
            stats = enqueuer.enqueue_human_readable_records(
                currency="ETH",
                probabilities_data={"2025-01-01": {"50000": {}}},
                pipeline=pipeline,
                sample_log_limit=5,
                verification_sample_limit=5,
            )

        assert stats.field_count == 0

    def test_sample_keys_limited(self) -> None:
        enqueuer = RecordEnqueuer()
        pipeline = _FakePipeline()

        records = [_make_record(key=f"k{i}") for i in range(5)]
        record_iter = iter(records)

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.build_probability_record",
                side_effect=record_iter,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.log_probability_diagnostics",
            ),
        ):
            stats = enqueuer.enqueue_human_readable_records(
                currency="BTC",
                probabilities_data={"2025-01-01": {f"strike{i}": {"p": 0.5} for i in range(5)}},
                pipeline=pipeline,
                sample_log_limit=2,
                verification_sample_limit=3,
            )

        assert len(stats.sample_keys) == 3

    def test_skips_none_event_ticker(self) -> None:
        enqueuer = RecordEnqueuer()
        pipeline = _FakePipeline()

        record_no_ticker = _make_record(event_ticker=None)

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.build_probability_record",
                return_value=record_no_ticker,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityingestion_helpers.record_enqueuer.log_probability_diagnostics",
            ),
        ):
            stats = enqueuer.enqueue_human_readable_records(
                currency="BTC",
                probabilities_data={"2025-01-01": {"50000": {"probability": 0.5}}},
                pipeline=pipeline,
                sample_log_limit=5,
                verification_sample_limit=5,
            )

        assert len(stats.event_ticker_counts) == 0
