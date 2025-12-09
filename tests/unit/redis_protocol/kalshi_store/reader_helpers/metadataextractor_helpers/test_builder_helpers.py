from datetime import datetime, timezone

import pytest

from src.common.redis_protocol.kalshi_store.market_skip import MarketSkip
from src.common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers import (
    field_extractor,
    metadata_builder,
    record_validator,
)


def _string_converter(value, default=""):
    if value in (None, "", b""):
        return default
    return str(value)


class _StubTimestampNormalizer:
    def normalize_timestamp(self, value):
        return value


class _StubStrikeResolver:
    def __init__(self, strike):
        self.strike = strike

    def resolve_strike_from_combined(self, _combined, _converter):
        return self.strike


class _StubTypeConverter:
    def normalize_hash(self, raw_hash):
        return dict(raw_hash)

    def string_or_default(self, value, default=""):
        if value in (None, "", b""):
            return default
        return str(value)


def test_extract_and_merge_metadata_and_validate_status():
    raw = {"metadata": b'{"foo": "bar"}', "status": "closed"}
    combined = field_extractor.extract_and_merge_metadata(raw, "MARKET")
    assert combined["foo"] == "bar"

    with pytest.raises(MarketSkip):
        field_extractor.validate_market_status(combined, "MARKET", _string_converter)


def test_extract_and_validate_close_time_and_strike():
    combined = {
        "close_time": "2025-01-01T00:00:00Z",
        "strike_type": "greater",
        "floor_strike": "12",
    }
    normalized = field_extractor.extract_and_validate_close_time(
        combined,
        "MARKET",
        _StubTimestampNormalizer(),
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert normalized == "2025-01-01T00:00:00Z"

    with pytest.raises(MarketSkip):
        field_extractor.extract_and_validate_close_time(
            {}, "MARKET", _StubTimestampNormalizer(), now=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    with pytest.raises(MarketSkip):
        field_extractor.extract_and_validate_strike(
            {}, "MARKET", _StubStrikeResolver(None), _string_converter
        )


def test_build_record_dict_uses_provided_values():
    combined = {
        "strike_type": "LESS",
        "floor_strike": "10",
        "cap_strike": "20",
        "event_ticker": "ET",
        "event_type": "TYPE",
        "yes_bid": "1",
        "yes_ask": "2",
    }
    record = field_extractor.build_record_dict(
        combined,
        market_ticker="TICKER",
        status_value="OPEN",
        normalized_close="2025-01-01T00:00:00Z",
        strike_value=5.0,
        currency="usd",
        string_converter=_string_converter,
    )
    assert record["currency"] == "USD"
    assert record["strike"] == 5.0
    assert record["event_ticker"] == "ET"


def test_metadata_builder_parses_and_builds_record():
    raw_hash = {"metadata": b'{"foo": "bar"}', "status": "open"}
    combined = metadata_builder.MetadataBuilder.build_combined(raw_hash, _StubTypeConverter())
    assert combined["foo"] == "bar"

    malformed = {"metadata": b"not json"}
    assert metadata_builder.MetadataBuilder._parse_metadata_json(malformed["metadata"]) == {}

    record = metadata_builder.MetadataBuilder.build_record(
        "TICK",
        combined,
        normalized_close="2025-01-01T00:00:00Z",
        strike_value=3.0,
        currency="usd",
        type_converter=_StubTypeConverter(),
    )
    assert record["ticker"] == "TICK"
    assert record["currency"] == "USD"


def test_record_validator_checks_fields():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_raw_hash({}, "MARKET")

    combined = {"status": "settled"}
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_market_status(
            combined, "MARKET", _StubTypeConverter()
        )

    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_not_expired(
            "2020-01-01T00:00:00Z", "MARKET", datetime(2021, 1, 1, tzinfo=timezone.utc)
        )

    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_close_time(None, "MARKET")

    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_strike(None, "MARKET")
