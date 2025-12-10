"""Tests for Redis market schema helpers."""

from datetime import datetime, timezone

import pytest

from common.redis_schema.markets import (
    DeribitInstrumentDescriptor,
    DeribitInstrumentKey,
    DeribitInstrumentType,
    KalshiMarketCategory,
    KalshiMarketKey,
    ReferenceMarketKey,
)


def _sample_timestamp() -> int:
    return int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())


def test_deribit_instrument_key_renders_segments():
    key = DeribitInstrumentKey(DeribitInstrumentType.FUTURE, "BTC", expiry_iso="2025-01-02").key()
    assert key.startswith("markets:deribit:future:btc:2025-01-02")


def test_kalshi_market_key_greenfield():
    key = KalshiMarketKey(KalshiMarketCategory.BINARY, "My Market").key()
    assert key == "markets:kalshi:binary:my_market"


def test_reference_market_key_djatify():
    key = ReferenceMarketKey("Deribit", "BTC-123").key()
    assert key == "reference:markets:deribit:btc-123"


def test_deribit_instrument_descriptor_spot():
    descriptor = DeribitInstrumentDescriptor.from_instrument_data(
        kind="spot",
        base_currency="btc",
        quote_currency="USD",
        expiration_timestamp=None,
        strike=None,
        option_type=None,
    )
    assert descriptor.instrument_type == DeribitInstrumentType.SPOT
    assert descriptor.quote_currency == "USD"
    assert descriptor.expiry_iso is None
    fields = descriptor.base_fields()
    assert fields["instrument_type"] == "spot"
    assert fields["currency"] == "BTC"


def test_deribit_instrument_descriptor_future():
    descriptor = DeribitInstrumentDescriptor.from_instrument_data(
        kind="future",
        base_currency="eth",
        quote_currency="usd",
        expiration_timestamp=_sample_timestamp(),
        strike=None,
        option_type=None,
    )
    assert descriptor.instrument_type == DeribitInstrumentType.FUTURE
    assert descriptor.expiry_iso == "2025-01-01"
    assert descriptor.expiry_token == "01JAN25"
    fields = descriptor.base_fields()
    assert fields["expiry_iso"] == "2025-01-01"
    assert fields["expiry_token"] == "01JAN25"


def test_deribit_instrument_descriptor_option_formats_strike():
    descriptor = DeribitInstrumentDescriptor.from_instrument_data(
        kind="option",
        base_currency="btc",
        quote_currency="usd",
        expiration_timestamp=_sample_timestamp(),
        strike=12.340000,
        option_type="call",
    )
    assert descriptor.instrument_type == DeribitInstrumentType.OPTION
    assert descriptor.strike == "12.34"
    assert descriptor.option_kind == "c"
    fields = descriptor.base_fields()
    assert fields["strike"] == "12.34"
    assert fields["option_kind"] == "c"


def test_format_strike_edge_cases():
    assert DeribitInstrumentDescriptor._format_strike(5.0) == "5"
    assert DeribitInstrumentDescriptor._format_strike(0.0012000) == "0.0012"
    assert DeribitInstrumentDescriptor._format_strike(0.0) == "0"


def test_deribit_descriptor_rejects_unknown_kind():
    with pytest.raises(ValueError, match="Unsupported Deribit instrument kind"):
        DeribitInstrumentDescriptor.from_instrument_data(
            kind="unknown",
            base_currency="btc",
            quote_currency="usd",
            expiration_timestamp=None,
            strike=None,
            option_type=None,
        )


def test_deribit_descriptor_rejects_missing_expiration_for_future():
    with pytest.raises(ValueError, match="missing expiration timestamp"):
        DeribitInstrumentDescriptor.from_instrument_data(
            kind="future",
            base_currency="btc",
            quote_currency="usd",
            expiration_timestamp=None,
            strike=None,
            option_type=None,
        )


def test_deribit_descriptor_rejects_missing_strike_for_option():
    with pytest.raises(ValueError, match="missing strike"):
        DeribitInstrumentDescriptor.from_instrument_data(
            kind="option",
            base_currency="btc",
            quote_currency="usd",
            expiration_timestamp=_sample_timestamp(),
            strike=None,
            option_type="call",
        )


def test_deribit_descriptor_rejects_missing_option_type():
    with pytest.raises(TypeError, match="missing option_type"):
        DeribitInstrumentDescriptor.from_instrument_data(
            kind="option",
            base_currency="btc",
            quote_currency="usd",
            expiration_timestamp=_sample_timestamp(),
            strike=1.0,
            option_type=None,
        )
