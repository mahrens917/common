import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

import src.common.redis_protocol.market_normalization as normalization_module
from src.common.redis_protocol import kalshi_store
from src.common.redis_protocol.kalshi_store import KalshiStore
from src.common.redis_protocol.market_normalization import (
    convert_numeric_field,
    derive_expiry_iso,
    format_probability_value,
    normalize_timestamp,
    parse_expiry_token,
    select_timestamp_value,
)

_CONST_12 = 12
_VAL_12_5 = 12.5
_CONST_15 = 15
_CONST_30 = 30
_TEST_COUNT_3 = 3
_TEST_ID_123 = 123

from src.common.redis_protocol.weather_station_resolver import (
    WeatherStationMappingError,
    WeatherStationResolver,
)
from src.common.redis_schema import KalshiMarketCategory, KalshiMarketDescriptor


@pytest.fixture
def store():
    resolver = WeatherStationResolver(lambda: {}, logger=logging.getLogger("tests.kalshi_utils"))
    return KalshiStore(service_prefix="ws", weather_resolver=resolver)


def test_convert_numeric_field_handles_strings_and_invalid():
    from src.common.exceptions import ValidationError

    assert convert_numeric_field("12.5") == pytest.approx(_VAL_12_5)
    assert convert_numeric_field("  ") is None
    with pytest.raises(ValidationError):
        convert_numeric_field("abc")
    with pytest.raises(TypeError):
        convert_numeric_field(["not", "numeric"])


def test_normalize_timestamp_supports_numeric_and_iso():
    iso_seconds = normalize_timestamp(1_700_000_000)
    assert iso_seconds == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc).isoformat()

    iso_millis = normalize_timestamp(1_700_000_000_000)
    assert (
        iso_millis == datetime.fromtimestamp(1_700_000_000_000 / 1000, tz=timezone.utc).isoformat()
    )

    iso_text = normalize_timestamp("2024-01-01T00:00:00Z")
    assert iso_text == "2024-01-01T00:00:00+00:00"

    invalid_text = normalize_timestamp("not-a-timestamp")
    assert invalid_text == "not-a-timestamp"

    assert normalize_timestamp(None) is None


def test_select_timestamp_value_returns_first_truthy():
    market_data = {"primary": "", "secondary": 0, "tertiary": 123}
    assert select_timestamp_value(market_data, ["primary", "secondary", "tertiary"]) == _TEST_ID_123
    assert select_timestamp_value({}, ["a", "b"]) is None


def test_parse_expiry_token_supports_year_day_format():
    result = parse_expiry_token("23MAR15")
    expected = datetime(2023, 3, 15, 23, 59, tzinfo=ZoneInfo("America/New_York")).astimezone(
        timezone.utc
    )
    assert result == expected


def test_parse_expiry_token_supports_intraday_format():
    token = "15MAR1230"
    result = parse_expiry_token(token)
    assert result is not None
    assert result.month == _TEST_COUNT_3
    assert result.day == _CONST_15
    assert result.tzinfo == timezone.utc
    assert result.hour == _CONST_12 and result.minute == _CONST_30


def test_parse_expiry_token_returns_none_for_invalid():
    assert parse_expiry_token("XXJUN24") is None
    assert parse_expiry_token("") is None


def test_derive_expiry_iso_prefers_existing_metadata():
    iso = "2024-05-01T00:00:00+00:00"
    descriptor = KalshiMarketDescriptor(
        key="market:SAMPLE",
        category=KalshiMarketCategory.BINARY,
        ticker="SAMPLE",
        underlying=None,
        expiry_token=None,
    )
    result = derive_expiry_iso(
        "SAMPLE",
        {"close_time": iso},
        descriptor=descriptor,
        token_parser=parse_expiry_token,
    )
    assert result == iso


def test_derive_expiry_iso_uses_expiry_token(monkeypatch):
    descriptor = KalshiMarketDescriptor(
        key="market:ABC",
        category=KalshiMarketCategory.BINARY,
        ticker="ABC",
        underlying=None,
        expiry_token="TOKEN",
    )
    target_dt = datetime(2026, 1, 2, tzinfo=timezone.utc)

    result = derive_expiry_iso(
        "ABC",
        {},
        descriptor=descriptor,
        token_parser=lambda token, now=None: (target_dt if token == "TOKEN" else None),
    )
    assert result == target_dt.isoformat()


def test_derive_expiry_iso_uses_future_timestamp():
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(microsecond=0)
    metadata = {"timestamp": str(future.timestamp())}

    descriptor = KalshiMarketDescriptor(
        key="market:XYZ-1",
        category=KalshiMarketCategory.BINARY,
        ticker="XYZ-1",
        underlying=None,
        expiry_token=None,
    )
    result = derive_expiry_iso(
        "XYZ-1",
        metadata,
        descriptor=descriptor,
        token_parser=lambda token, now=None: None,
    )
    assert datetime.fromisoformat(result) == future


def test_derive_expiry_iso_errors_when_timestamp_in_past():
    from src.common.exceptions import DataError

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    metadata = {"timestamp": str(past.timestamp())}

    descriptor = KalshiMarketDescriptor(
        key="market:NOSEGMENT",
        category=KalshiMarketCategory.BINARY,
        ticker="NOSEGMENT",
        underlying=None,
        expiry_token=None,
    )
    with pytest.raises(DataError):
        derive_expiry_iso(
            "NOSEGMENT",
            metadata,
            descriptor=descriptor,
            token_parser=lambda token, now=None: None,
            now=datetime.now(timezone.utc),
        )


def test_derive_expiry_iso_errors_when_metadata_missing(monkeypatch):
    from src.common.exceptions import DataError

    descriptor = KalshiMarketDescriptor(
        key="market:ABC",
        category=KalshiMarketCategory.BINARY,
        ticker="ABC",
        underlying=None,
        expiry_token=None,
    )

    base_now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    with pytest.raises(DataError):
        derive_expiry_iso(
            "ABC",
            {},
            descriptor=descriptor,
            token_parser=lambda token, now=None: None,
            now=base_now,
        )


# test_kalshi_store_handles_weather_loader_failure removed - weather resolver initialization is now lazy/optional


def test_resolve_city_alias_and_station_lookup():
    resolver = WeatherStationResolver(
        lambda: {
            "PHIL": {"icao": "KPHL"},
            "NYC": {"icao": "KJFK", "aliases": ["NYNY"]},
        },
        logger=logging.getLogger("tests.weather"),
    )

    assert resolver.resolve_city_alias("NYNY") == "NYC"
    assert resolver.resolve_city_alias("PHIL") is None

    direct = resolver.extract_station("KXHIGHPHIL-25AUG31-B80.5")
    alias = resolver.extract_station("KXHIGHNYNY-25AUG30-T100")
    unrelated = resolver.extract_station("NONWEATHER-XYZ")

    assert direct == "KPHL"
    assert alias == "KJFK"
    assert unrelated is None


def test_format_probability_value_trims_trailing_zeroes():
    assert format_probability_value(0.1234000) == "0.1234"
    assert format_probability_value("0.5000") == "0.5"

    with pytest.raises(TypeError):
        format_probability_value(float("inf"))

    with pytest.raises(TypeError):
        format_probability_value("not-a-number")
