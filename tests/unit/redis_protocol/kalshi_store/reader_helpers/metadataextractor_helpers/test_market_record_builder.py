from datetime import datetime, timezone

import pytest

from common.redis_protocol.kalshi_store.market_skip import MarketSkip
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder import (
    MarketRecordBuilder,
    _decode_metadata_payload,
)


class StubTypeConverter:
    def normalize_hash(self, raw_hash):
        return dict(raw_hash)

    def string_or_default(self, value, default=""):
        if value in (None, ""):
            return default
        return str(value)


class StubTimestampNormalizer:
    def __init__(self, value):
        self.value = value

    def normalize_timestamp(self, _value):
        return self.value


class StubStrikeResolver:
    def __init__(self, value):
        self.value = value

    def resolve_strike_from_combined(self, combined, string_converter):
        return self.value


def _build_raw_hash():
    return {
        "metadata": b'{"event_ticker": "EV", "event_type": "TYPE"}',
        "status": "OPEN",
        "close_time": "2025-01-01T00:00:00Z",
        "strike_type": "BETWEEN",
        "floor_strike": "10",
        "cap_strike": "20",
        "yes_bid": "1",
        "yes_ask": "2",
        "yes_bids": "[1]",
        "yes_asks": "[2]",
    }


@pytest.fixture(autouse=True)
def patch_build_key(monkeypatch):
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder.build_kalshi_market_key",
        lambda ticker: f"key-{ticker}",
    )
    yield


def test_market_record_builder_succeeds():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer("2025-01-01T00:00:00Z"),
        strike_resolver=StubStrikeResolver(15.0),
    )
    record = builder.create_market_record(
        "ABC",
        _build_raw_hash(),
        currency="usd",
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    assert record["ticker"] == "ABC"
    assert record["market_key"] == "key-ABC"
    assert record["status"] == "OPEN"
    assert record["close_time"] == "2025-01-01T00:00:00Z"
    assert record["strike"] == 15.0
    assert record["currency"] == "USD"
    assert record["event_ticker"] == "EV"


def test_market_record_builder_missing_hash_raises():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer("2025-01-01T00:00:00Z"),
        strike_resolver=StubStrikeResolver(1.0),
    )
    with pytest.raises(MarketSkip) as exc:
        builder.create_market_record("ABC", {}, currency="usd", now=datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert exc.value.reason == "missing_metadata"


def test_market_record_builder_closed_status_raises():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer("2025-01-01T00:00:00Z"),
        strike_resolver=StubStrikeResolver(1.0),
    )
    raw_hash = _build_raw_hash()
    raw_hash["status"] = "closed"
    with pytest.raises(MarketSkip):
        builder.create_market_record("ABC", raw_hash, currency="usd", now=datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_market_record_builder_missing_close_time_raises():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer(""),
        strike_resolver=StubStrikeResolver(1.0),
    )
    raw_hash = _build_raw_hash()
    raw_hash.pop("close_time", None)
    with pytest.raises(MarketSkip):
        builder.create_market_record("ABC", raw_hash, currency="usd", now=datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_market_record_builder_expired_close_time_raises():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer("2023-01-01T00:00:00Z"),
        strike_resolver=StubStrikeResolver(1.0),
    )
    with pytest.raises(MarketSkip):
        builder.create_market_record("ABC", _build_raw_hash(), currency="usd", now=datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_market_record_builder_missing_strike_raises():
    builder = MarketRecordBuilder(
        type_converter=StubTypeConverter(),
        timestamp_normalizer=StubTimestampNormalizer("2025-01-01T00:00:00Z"),
        strike_resolver=StubStrikeResolver(None),
    )
    with pytest.raises(MarketSkip):
        builder.create_market_record("ABC", _build_raw_hash(), currency="usd", now=datetime(2024, 1, 1, tzinfo=timezone.utc))


def test_decode_metadata_payload_handles_invalid():
    raw = b"not json"
    assert _decode_metadata_payload(raw, "ABC") == {}
