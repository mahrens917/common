from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pytest

from common.redis_protocol.kalshi_store.market_skip import MarketSkip
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers import (
    field_extractor as field_helpers,
)
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers import (
    metadata_builder,
    record_validator,
)
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.metadata_parser import (
    MetadataParser,
)
from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.price_extractor import (
    PriceExtractor,
)
from common.strike_helpers import calculate_strike_value, parse_strike_bounds


def _string_converter(value: Any, fallback: Optional[Any] = None) -> Any:
    if value in (None, "", b""):
        return fallback
    return str(value)


class DummyTimestampNormalizer:
    def __init__(self, normalized: str) -> None:
        self.normalized = normalized

    def normalize_timestamp(self, _value: Any) -> str:
        return self.normalized


class DummyStrikeResolver:
    def __init__(self, strike: Optional[float]) -> None:
        self.strike = strike

    def resolve_strike_from_combined(self, _combined: Dict[str, Any], _converter: Any) -> Optional[float]:
        return self.strike


class DummyTypeConverter:
    def normalize_hash(self, raw_hash: Dict[str, Any]) -> Dict[str, Any]:
        return raw_hash

    def string_or_default(self, value: Any, fallback: Optional[Any] = None) -> Any:
        if value in (None, "", b""):
            return fallback
        return str(value)


def test_extract_and_merge_metadata_merges_json_payload():
    raw = {
        "metadata": b'{"status": "live", "extra": 1}',
        "yes_bid": "10",
    }

    combined = field_helpers.extract_and_merge_metadata(raw, "KXHIGHZ")

    assert combined["status"] == "live"
    assert combined["extra"] == 1
    assert combined["yes_bid"] == "10"


def test_extract_and_merge_metadata_handles_invalid_json():
    raw = {"metadata": b"[]}", "yes_bid": "10"}

    combined = field_helpers.extract_and_merge_metadata(raw, "KXHIGHZ")

    assert combined["yes_bid"] == "10"
    assert "extra" not in combined


def test_validate_market_status_raises_on_terminal_status():
    combined = {"status": "Settled"}

    with pytest.raises(MarketSkip):
        field_helpers.validate_market_status(combined, "KXHIGHZ", _string_converter)


def test_extract_and_validate_close_time_success():
    normalized = "2024-01-01T00:00:00Z"
    now = datetime(2023, 12, 31, tzinfo=timezone.utc)
    combined = {"close_time": "2024-01-01T00:00:00Z"}
    normalizer = DummyTimestampNormalizer(normalized)

    result = field_helpers.extract_and_validate_close_time(combined, "KXHIGHZ", normalizer, now)

    assert result == normalized


def test_extract_and_validate_close_time_handles_missing():
    combined: Dict[str, Any] = {}
    now = datetime.now(timezone.utc)
    normalizer = DummyTimestampNormalizer("2025-01-01T00:00:00Z")

    with pytest.raises(MarketSkip):
        field_helpers.extract_and_validate_close_time(combined, "KXHIGHZ", normalizer, now)


def test_extract_and_validate_close_time_detects_expired():
    normalized = "2022-01-01T00:00:00Z"
    now = datetime(2023, 1, 2, tzinfo=timezone.utc)
    combined = {"close_time": "2022-01-01T00:00:00Z"}
    normalizer = DummyTimestampNormalizer(normalized)

    with pytest.raises(MarketSkip):
        field_helpers.extract_and_validate_close_time(combined, "KXHIGHZ", normalizer, now)


def test_extract_and_validate_strike_raises_when_missing():
    resolver = DummyStrikeResolver(None)

    with pytest.raises(MarketSkip):
        field_helpers.extract_and_validate_strike({}, "KXHIGHZ", resolver, _string_converter)


def test_build_record_dict_applies_converters():
    combined = {
        "strike_type": "CALL",
        "floor_strike": "12",
        "cap_strike": "15",
        "event_ticker": "EVT",
        "event_type": "TYPE",
        "yes_bid": 1.2,
        "yes_ask": 1.3,
    }

    result = field_helpers.build_record_dict(
        combined,
        "KXHIGHZ",
        "open",
        "2025-01-01T00:00:00Z",
        123.4,
        "usd",
        _string_converter,
    )

    assert result["currency"] == "USD"
    assert result["strike_type"] == "CALL"
    assert result["strike"] == 123.4


def test_metadata_builder_combines_snapshot_and_metadata():
    raw_hash = {
        "metadata": b'{"status": "live"}',
        "other": "value",
    }
    converter = DummyTypeConverter()

    combined = metadata_builder.MetadataBuilder.build_combined(raw_hash, converter)

    assert combined["status"] == "live"
    assert combined["other"] == "value"


def test_metadata_builder_parses_invalid_json():
    result = metadata_builder.MetadataBuilder._parse_metadata_json(b"bad")

    assert result == {}


def test_metadata_builder_build_record_uses_converter():
    combined = {"status": "settled", "strike_type": "CALL", "floor_strike": "1"}
    converter = DummyTypeConverter()

    record = metadata_builder.MetadataBuilder.build_record("KXHIGHZ", combined, "time", 1.0, "eur", converter)

    assert record["currency"] == "EUR"
    assert record["status"] == "settled"


def test_record_validator_flags_bad_hash():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_raw_hash({}, "KXHIGHZ")


def test_record_validator_captures_terminal_status():
    combined = {"status": "closed"}

    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_market_status(combined, "KXHIGHZ", DummyTypeConverter())


def test_record_validator_detects_expired_date():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_not_expired(
            "2020-01-01T00:00:00Z",
            "KXHIGHZ",
            datetime(2021, 1, 1, tzinfo=timezone.utc),
        )


def test_record_validator_handles_invalid_close_time():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_close_time(None, "KXHIGHZ")


def test_record_validator_handles_missing_strike():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_strike(None, "KXHIGHZ")


def test_metadata_parser_returns_parsed_metadata():
    result = MetadataParser.parse_market_metadata("KXHIGHZ", {"metadata": b'{"foo": "bar"}'})

    assert result == {"foo": "bar"}


def test_metadata_parser_handles_invalid_json():
    assert MetadataParser.parse_market_metadata("KXHIGHZ", {"metadata": b"broken"}) is None


def test_metadata_parser_missing_metadata():
    assert MetadataParser.parse_market_metadata("KXHIGHZ", {}) is None


def test_price_extractor_coerces_prices():
    metadata = {"yes_bid": "2.5", "yes_ask": "bad"}

    assert PriceExtractor.extract_market_prices(metadata) == (2.5, None)


def test_strike_helpers_convert_bounds():
    floor_val, cap_val = parse_strike_bounds("5", None)
    assert floor_val == 5.0
    assert cap_val is None

    floor_val, cap_val = parse_strike_bounds("", "")
    assert floor_val is None
    assert cap_val is None

    floor_val, cap_val = parse_strike_bounds(b"6", None)
    assert floor_val == 6.0

    assert calculate_strike_value("between", 1.0, 3.0) == 2.0
    assert calculate_strike_value("greater", 4.0, None) == 4.0
    assert calculate_strike_value("less", None, 7.0) == 7.0
    assert calculate_strike_value("unknown", 8.0, None) is None
    assert calculate_strike_value("unknown", None, None) is None


def test_strike_helpers_calculate_values():
    floor_val, cap_val = parse_strike_bounds("10", None)
    assert calculate_strike_value("greater", floor_val, cap_val) == 10.0

    floor_val, cap_val = parse_strike_bounds("5", "7")
    assert calculate_strike_value("between", floor_val, cap_val) == 6.0
