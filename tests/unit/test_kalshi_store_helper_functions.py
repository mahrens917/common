import logging
from datetime import timezone

import pytest

from common.market_filters.kalshi import parse_expiry_datetime
from common.redis_protocol.market_metadata_builder import build_market_metadata
from common.redis_protocol.market_normalization import convert_numeric_field
from common.redis_protocol.weather_station_resolver import WeatherStationResolver
from common.redis_schema import describe_kalshi_ticker

_VAL_1_25 = 1.25
_VAL_2_0 = 2.0


def test_parse_expiry_datetime_handles_z_suffix():
    dt = parse_expiry_datetime("2025-01-01T00:00:00Z")
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc


def test_convert_numeric_field_handles_inputs():
    assert convert_numeric_field("1.25") == _VAL_1_25
    assert convert_numeric_field(2) == _VAL_2_0
    assert convert_numeric_field("") is None
    assert convert_numeric_field(None) is None


def test_weather_station_resolver_with_alias():
    resolver = WeatherStationResolver(
        lambda: {"TEST": {"icao": "KTEST", "aliases": ["ALTS"]}},
        logger=logging.getLogger("tests.helpers"),
    )

    assert resolver.extract_station("KXHIGHTEST-25AUG31-B80") == "KTEST"
    assert resolver.extract_station("KXHIGHALTS-25AUG31-B80") == "KTEST"
    assert resolver.resolve_city_alias("ALTS") == "TEST"


def test_build_market_metadata_populates_required_fields(monkeypatch):
    descriptor = describe_kalshi_ticker("KXHIGHNYC-25JAN20-B080")
    market_data = {
        "id": "market-123",
        "strike_type": "Greater",
        "floor_strike": 80,
        "close_time": "2025-01-31T00:00:00Z",
        "open_time": "2025-01-01T00:00:00Z",
        "expected_expiration_time": "2025-01-31T00:00:00Z",
        "expiration_time": "2025-01-31T00:00:00Z",
        "latest_expiration_time": "2025-01-31T00:00:00Z",
        "fee_waiver_expiration_time": "2025-01-15T00:00:00Z",
        "tick_size": 3,
    }
    event_data = {"ticker": "EVT", "mutually_exclusive": True}

    class StubResolver:
        def extract_station(self, ticker: str) -> str:
            assert ticker == "KXHIGHNYC-25JAN20-B080"
            return "KNYC"

    monkeypatch.setattr("common.redis_protocol.market_metadata_builder.time.time", lambda: 123)

    metadata = build_market_metadata(
        market_ticker="KXHIGHNYC-25JAN20-B080",
        market_data=market_data,
        event_data=event_data,
        descriptor=descriptor,
        weather_resolver=StubResolver(),
        logger=logging.getLogger("tests.helpers"),
    )

    assert metadata["close_time"] == "2025-01-31T00:00:00+00:00"
    assert metadata["floor_strike"] == "80"
    assert metadata["cap_strike"] == ""
    assert metadata["strike_type"] == "Greater"
    assert metadata["weather_station"] == "KNYC"
    assert metadata["timestamp"] == "123"
    assert metadata["event_ticker"] == "EVT"
    assert metadata["mutually_exclusive"] == "true"
    # Orderbook fields (yes_bids, yes_asks, etc) are not set by REST -
    # they come exclusively from websocket snapshots/deltas
    assert "yes_bids" not in metadata
    assert "yes_bid" not in metadata


def test_build_market_metadata_requires_close_time():
    descriptor = describe_kalshi_ticker("KXHIGHCHI-25JAN20-B080")
    market_data = {
        "id": "market-456",
        "strike_type": "Less",
        "cap_strike": 75,
    }

    metadata = build_market_metadata(
        market_ticker="KXHIGHCHI-25JAN20-B080",
        market_data=market_data,
        event_data=None,
        descriptor=descriptor,
        weather_resolver=None,
        logger=logging.getLogger("tests.helpers"),
    )

    assert metadata["close_time"] == ""


def test_build_market_metadata_handles_missing_strike_type():
    descriptor = describe_kalshi_ticker("KXFIRSTSUPERBOWLSONG-26FEB09-DAK")
    market_data = {
        "id": "market-789",
        "close_time": "2026-02-09T00:00:00Z",
    }

    metadata = build_market_metadata(
        market_ticker="KXFIRSTSUPERBOWLSONG-26FEB09-DAK",
        market_data=market_data,
        event_data=None,
        descriptor=descriptor,
        weather_resolver=None,
        logger=logging.getLogger("tests.helpers"),
    )

    assert metadata["strike_type"] == ""
    assert metadata["floor_strike"] == ""
    assert metadata["cap_strike"] == ""
    assert metadata["close_time"] == "2026-02-09T00:00:00+00:00"
