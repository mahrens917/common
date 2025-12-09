"""Tests for the market record field extractor."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.market_skip import MarketSkip
from src.common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.market_record_builder_helpers.field_extractor import (
    build_record_dict,
    extract_and_merge_metadata,
    extract_and_validate_close_time,
    extract_and_validate_strike,
    validate_market_status,
)


def _string_converter(value, fallback=None):
    if value is None:
        return fallback
    return str(value)


def test_extract_and_merge_metadata_merges_json():
    raw = {"metadata": b'{"foo": "bar"}', "status": "open"}
    combined = extract_and_merge_metadata(raw, "T")
    assert combined["foo"] == "bar"
    assert combined["status"] == "open"


def test_extract_and_merge_metadata_handles_bad_json(monkeypatch):
    raw = {"metadata": b"{bad", "status": "open"}
    combined = extract_and_merge_metadata(raw, "T")
    assert combined["status"] == "open"


def test_validate_market_status_allows_open():
    combined = {"status": "open"}
    validate_market_status(combined, "T", _string_converter)


def test_validate_market_status_raises_when_closed():
    combined = {"status": "closed"}
    with pytest.raises(MarketSkip):
        validate_market_status(combined, "T", _string_converter)


def test_extract_and_validate_close_time_handles_missing():
    combined = {}
    normalizer = MagicMock()
    with pytest.raises(MarketSkip):
        extract_and_validate_close_time(combined, "T", normalizer, datetime.now(timezone.utc))


def test_extract_and_validate_close_time_checks_expiry():
    target = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    combined = {"close_time": target}
    normalizer = MagicMock()
    normalizer.normalize_timestamp.return_value = target
    with pytest.raises(MarketSkip):
        extract_and_validate_close_time(combined, "T", normalizer, datetime.now(timezone.utc))


def test_extract_and_validate_close_time_returns_normalized():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    combined = {"close_time": future}
    normalizer = MagicMock()
    normalizer.normalize_timestamp.return_value = future
    assert (
        extract_and_validate_close_time(combined, "T", normalizer, datetime.now(timezone.utc))
        == future
    )


def test_extract_and_validate_strike_raises_when_missing():
    combined = {}
    resolver = MagicMock()
    resolver.resolve_strike_from_combined.return_value = None
    with pytest.raises(MarketSkip):
        extract_and_validate_strike(combined, "T", resolver, _string_converter)


def test_extract_and_validate_strike_returns_value():
    combined = {}
    resolver = MagicMock()
    resolver.resolve_strike_from_combined.return_value = 12.5
    assert extract_and_validate_strike(combined, "T", resolver, _string_converter) == 12.5


def test_build_record_dict_sets_fields():
    combined = {
        "strike_type": "CALL",
        "floor_strike": 1,
        "cap_strike": 10,
        "event_ticker": "EX",
        "event_type": "E",
        "yes_bid": 4,
        "yes_ask": 5,
    }
    string_converter = lambda value, fallback=None: str(value) if value is not None else fallback
    record = build_record_dict(
        combined,
        "KXHIGHABC",
        "OPEN",
        "2024-01-01T00:00:00Z",
        2.0,
        "usd",
        string_converter,
    )

    assert record["ticker"] == "KXHIGHABC"
    assert record["strike"] == 2.0
    assert record["currency"] == "USD"
    assert record["status"] == "OPEN"
