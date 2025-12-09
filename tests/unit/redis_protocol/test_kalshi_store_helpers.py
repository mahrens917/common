from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.common.redis_protocol.kalshi_store import KalshiStore
from src.common.redis_protocol.kalshi_store.store_initializer import initialize_kalshi_store
from src.common.redis_protocol.orderbook_utils import (
    build_snapshot_sides,
    merge_orderbook_payload,
)
from src.common.redis_protocol.parsing import derive_strike_fields, parse_expiry_token
from src.common.redis_protocol.weather_station_resolver import WeatherStationResolver

_CONST_15 = 15
_CONST_2025 = 2025
_CONST_30 = 30
_TEST_COUNT_9 = 9


def _make_store(**overrides) -> KalshiStore:
    logger = overrides.pop("logger", logging.getLogger("kalshi-store-tests"))
    redis = overrides.pop("redis", None)
    weather_resolver = overrides.pop(
        "weather_resolver", WeatherStationResolver(lambda: {}, logger=logger)
    )

    store = KalshiStore.__new__(KalshiStore)
    initialize_kalshi_store(store, redis, "ws", weather_resolver)

    for key, value in overrides.items():
        setattr(store, key, value)
    return store


def test_normalise_hash_with_bytes():
    raw = {b"field": b"value", "other": "ok"}
    result = KalshiStore._normalise_hash(raw)
    assert result == {"field": "value", "other": "ok"}


def test_sync_top_of_book_fields_updates_snapshot():
    snapshot = {
        "yes_bids": '{"45": 3, "40": 2}',
        "yes_asks": '{"50": 4, "55": 1}',
    }
    KalshiStore._sync_top_of_book_fields(snapshot)
    assert snapshot["yes_bid"] == "45.0"
    assert snapshot["yes_bid_size"] == "3"
    assert snapshot["yes_ask"] == "50.0"
    assert snapshot["yes_ask_size"] == "4"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.123450000", "0.12345"),
        (0.75, "0.75"),
        ("1", "1"),
    ],
)
def test_format_probability_value_success(value, expected):
    assert KalshiStore._format_probability_value(value) == expected


@pytest.mark.parametrize("value", ["nan", "abc", None])
def test_format_probability_value_errors(value):
    with pytest.raises(TypeError):
        KalshiStore._format_probability_value(value)


def test_extract_weather_station_from_ticker_with_resolver():
    store = _make_store(
        weather_resolver=SimpleNamespace(extract_station=lambda ticker: "KJFK"),
    )
    assert store._extract_weather_station_from_ticker("KXHIGHNYC-25AUG31-B80") == "KJFK"
    assert store._extract_weather_station_from_ticker("SP500-XYZ") is None


def test_parse_expiry_token_variants():
    result = parse_expiry_token("25AUG31")
    assert result.year == _CONST_2025 and result.month == _TEST_COUNT_9 and result.day == 1

    result_time = parse_expiry_token("20AUG1530")
    assert result_time.hour == _CONST_15 and result_time.minute == _CONST_30


def test_derive_expiry_iso_uses_descriptor(monkeypatch):
    store = _make_store()
    descriptor = SimpleNamespace(
        expiry_token="25AUG31",
        key="kalshi:KX-TEST",
    )
    # Mock describe_kalshi_ticker to return our custom descriptor
    monkeypatch.setattr("src.common.redis_schema.describe_kalshi_ticker", lambda ticker: descriptor)
    # Provide a close_time that the function can parse
    metadata = {"close_time": "2025-08-31T03:59:00Z"}
    iso_value = store._derive_expiry_iso("KX-TEST", metadata)
    # Both 'Z' and '+00:00' represent UTC
    assert iso_value.endswith("T03:59:00Z") or iso_value.endswith("T03:59:00+00:00")


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("KXHIGH-FOO-B80", ("less", None, 80.0, 80.0)),
        ("KXHIGH-FOO-T100", ("greater", 100.0, None, 100.0)),
        ("KXHIGH-FOO-M50", ("between", None, None, 50.0)),
    ],
)
def test_derive_strike_fields_variants(ticker, expected):
    assert derive_strike_fields(ticker) == expected


def test_ensure_market_metadata_fields_populates_defaults():
    store = _make_store()
    metadata = {
        "close_time_ms": str(int(datetime(2024, 8, 31, tzinfo=timezone.utc).timestamp() * 1000)),
        "status": "halted",
    }
    enriched = store._ensure_market_metadata_fields("KXHIGHAAA-25AUG31-B80", metadata)
    assert enriched["strike_type"] == "less"
    assert enriched["cap_strike"] == "80.0"
    assert enriched["floor_strike"] == "0"
    assert enriched["close_time"].endswith("T00:00:00+00:00")
    assert enriched["status"] == "halted"


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        (0, "1970-01-01T00:00:00+00:00"),
        (1693180800, "2023-08-28T00:00:00+00:00"),
        (1693180800000, "2023-08-28T00:00:00+00:00"),
        ("2024-08-20T12:30:00Z", "2024-08-20T12:30:00+00:00"),
    ],
)
def test_normalize_timestamp_numeric_and_iso(input_value, expected):
    result = KalshiStore._normalize_timestamp(input_value)
    assert result == expected


def test_normalize_timestamp_returns_original_for_unknown_format():
    assert KalshiStore._normalize_timestamp("not-a-date") == "not-a-date"


def test_aggregate_markets_by_point_and_summary():
    store = _make_store()
    markets = [
        {
            "expiry": "2024-09-01T00:00:00+00:00",
            "strike": "80",
            "strike_type": "less",
            "market_ticker": "KX-1",
            "floor_strike": "0",
            "cap_strike": "80",
        },
        {
            "expiry": "2024-09-01T00:00:00+00:00",
            "strike": "80",
            "strike_type": "less",
            "market_ticker": "KX-2",
        },
    ]
    grouped, market_by_ticker = store._aggregate_markets_by_point(markets)
    summary = store._build_strike_summary(grouped, market_by_ticker)
    assert list(summary.keys()) == ["2024-09-01T00:00:00+00:00"]
    strike_entry = summary["2024-09-01T00:00:00+00:00"][0]
    assert strike_entry["market_tickers"] == ["KX-1", "KX-2"]
    assert strike_entry["floor_strike"] == 0.0


def test_merge_orderbook_payload_combines_sections():
    message = {
        "type": "snapshot",
        "msg": {"market_ticker": "KX-TEST"},
        "data": {
            "orderbook": {"yes_bids": {"45": 5}},
            "levels": {"yes": [[45, 5]], "no": [[60, 7]]},
        },
    }
    msg_type, msg_data, ticker = merge_orderbook_payload(message)
    assert msg_type == "snapshot"
    assert msg_data["yes_bids"] == {"45": 5}
    assert msg_data["yes"] == [[45, 5]]
    assert ticker == "KX-TEST"


def test_build_snapshot_sides_converts_no_side():
    msg_data = {
        "yes": [[45, 5]],
        "no": [[55, 3]],
    }
    sides = build_snapshot_sides(msg_data, "KX-TEST")
    assert sides["yes_bids"] == {"45.0": 5.0}
    assert sides["yes_asks"] == {"45.0": 3.0}


@pytest.mark.parametrize(
    ("value", "assertion"),
    [
        ("2024-08-20T12:00:00Z", lambda v: v.endswith("12:00:00+00:00")),
        (1692542400, lambda v: v.endswith("2023-08-20T12:00:00+00:00")),
        ("bad-value", lambda v: v == ""),
    ],
)
def test_normalise_trade_timestamp(value, assertion):
    result = KalshiStore._normalise_trade_timestamp(value)
    assertion(result)
