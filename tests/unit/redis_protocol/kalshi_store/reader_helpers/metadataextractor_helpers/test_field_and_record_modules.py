from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from src.common.redis_protocol.kalshi_store.market_skip import MarketSkip
from src.common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers import (
    field_extractor,
    metadata_builder,
    record_validator,
)


class DummyStrikeResolver:
    def __init__(self, strike: float | None):
        self._strike = strike

    def resolve_strike_from_combined(
        self, combined: Dict[str, Any], converter: Any
    ) -> float | None:
        return self._strike


class DummyNormalizer:
    def __init__(self, normalized: str = "2025-01-01T00:00:00Z") -> None:
        self.normalized = normalized

    def normalize_timestamp(self, _value: Any) -> str:
        return self.normalized


class DummyTypeConverter:
    def normalize_hash(self, raw_hash: Dict[str, Any]) -> Dict[str, Any]:
        return raw_hash

    def string_or_default(self, value: Any, fallback: Any = "") -> Any:
        return str(value) if value is not None else fallback


def test_extract_and_merge_metadata_combines_values():
    raw = {"metadata": b'{"a": 1}', "status": "live"}
    combined = field_extractor.extract_and_merge_metadata(raw, "KXHIGHTEST")

    assert combined["a"] == 1
    assert combined["status"] == "live"


def test_extract_and_merge_metadata_handles_invalid_json(caplog):
    raw = {"metadata": b"invalid", "status": "live"}
    caplog.set_level(logging.DEBUG, logger=field_extractor.__name__)
    combined = field_extractor.extract_and_merge_metadata(raw, "KXHIGHTEST")

    assert combined["status"] == "live"
    assert "Failed to decode metadata JSON" in caplog.text


def test_validate_market_status_raises_on_closed():
    with pytest.raises(MarketSkip):
        field_extractor.validate_market_status({"status": "closed"}, "ticker", str)


def test_extract_and_validate_close_time_requires_value():
    with pytest.raises(MarketSkip):
        field_extractor.extract_and_validate_close_time(
            {}, "ticker", DummyNormalizer(), datetime.now(timezone.utc)
        )


def test_extract_and_validate_close_time_detects_expired():
    now = datetime(2020, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(MarketSkip):
        field_extractor.extract_and_validate_close_time(
            {"close_time": "2020-01-01T00:00:00Z"},
            "ticker",
            DummyNormalizer("2020-01-01T00:00:00Z"),
            now,
        )


def test_extract_and_validate_strike_requires_value():
    with pytest.raises(MarketSkip):
        field_extractor.extract_and_validate_strike({}, "ticker", DummyStrikeResolver(None), str)


def test_field_extractor_build_record_dict_converts():
    combined = {"strike_type": "CALL", "floor_strike": "1", "cap_strike": "2"}

    def converter(value, fallback=None):
        if value in (None, "", b""):
            return fallback
        return str(value)

    record = field_extractor.build_record_dict(
        combined,
        "ticker",
        "live",
        "2025-01-01T00:00:00Z",
        1.23,
        "usd",
        converter,
    )

    assert record["currency"] == "USD"
    assert record["strike"] == 1.23


def test_metadata_builder_build_combined_handles_metadata_json():
    raw = {"metadata": b'{"foo": "bar"}', "baz": "qux"}
    converter = DummyTypeConverter()
    result = metadata_builder.MetadataBuilder.build_combined(raw, converter)

    assert result["foo"] == "bar"
    assert result["baz"] == "qux"


def test_metadata_builder_parses_empty_metadata():
    assert metadata_builder.MetadataBuilder._parse_metadata_json(None) == {}


def test_metadata_builder_build_record_uses_converter():
    converter = DummyTypeConverter()
    combined = {"status": "live", "strike_type": "CALL", "floor_strike": "1"}
    record = metadata_builder.MetadataBuilder.build_record(
        "ticker",
        combined,
        "expiry",
        1.5,
        "usd",
        converter,
    )

    assert record["status"] == "live"
    assert record["strike"] == 1.5


def test_record_validator_raises_on_missing_hash():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_raw_hash({}, "ticker")


def test_record_validator_detects_terminal_status():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_market_status(
            {"status": "settled"}, "ticker", DummyTypeConverter()
        )


def test_record_validator_detects_expired(normalizer=DummyNormalizer()):
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_not_expired(
            "2020-01-01T00:00:00Z", "ticker", datetime(2021, 1, 2, tzinfo=timezone.utc)
        )


def test_record_validator_missing_close_time():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_close_time(None, "ticker")


def test_record_validator_missing_strike():
    with pytest.raises(MarketSkip):
        record_validator.RecordValidator.validate_strike(None, "ticker")
