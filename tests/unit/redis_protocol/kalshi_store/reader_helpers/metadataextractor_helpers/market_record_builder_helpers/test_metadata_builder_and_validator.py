"""Tests for metadata builder and validator utilities."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from common.redis_protocol.kalshi_store.market_skip import MarketSkip
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers.metadata_builder import (
    MetadataBuilder,
)
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers.record_validator import (
    RecordValidator,
)


class DummyTypeConverter:
    def normalize_hash(self, raw_hash):
        normalized = dict(raw_hash)
        normalized["metadata"] = raw_hash.get("metadata")
        return normalized

    def string_or_default(self, value, fallback=None):
        if value is None:
            return fallback
        return str(value)


def test_build_combined_merges_json():
    raw = {"metadata": b'{"foo": "bar"}', "status": "open"}
    combined = MetadataBuilder.build_combined(raw, DummyTypeConverter())
    assert combined["foo"] == "bar"


def test_build_combined_handles_bad_json():
    raw = {"metadata": b"{bad", "status": "open"}
    combined = MetadataBuilder.build_combined(raw, DummyTypeConverter())
    assert combined["status"] == "open"


def test_build_record_sets_expected_fields():
    combined = {
        "status": "open",
        "strike_type": "CALL",
        "floor_strike": 1,
        "cap_strike": 2,
        "event_ticker": "ET",
        "event_type": "EV",
        "yes_bid": 3,
        "yes_ask": 4,
    }
    record = MetadataBuilder.build_record(
        "KXHIGHABC",
        combined,
        "2024-01-01T00:00:00Z",
        1.5,
        "usd",
        DummyTypeConverter(),
    )
    assert record["strike"] == 1.5
    assert record["currency"] == "USD"


def test_validate_raw_hash_raises_when_empty():
    with pytest.raises(MarketSkip):
        RecordValidator.validate_raw_hash({}, "T")


def test_validate_market_status_raises_on_settled():
    combined = {"status": "settled"}
    with pytest.raises(MarketSkip):
        RecordValidator.validate_market_status(combined, "T", DummyTypeConverter())


def test_validate_not_expired_raises_when_past():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    now = datetime.now(timezone.utc)
    with pytest.raises(MarketSkip):
        RecordValidator.validate_not_expired(past, "T", now)


def test_validate_not_expired_allows_future():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    now = datetime.now(timezone.utc)
    RecordValidator.validate_not_expired(future, "T", now)


def test_validate_close_time_and_strike_raise_when_missing():
    with pytest.raises(MarketSkip):
        RecordValidator.validate_close_time(None, "T")
    with pytest.raises(MarketSkip):
        RecordValidator.validate_strike(None, "T")
