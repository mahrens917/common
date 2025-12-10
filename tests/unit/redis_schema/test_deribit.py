import pytest

from common.redis_schema.deribit import parse_deribit_market_key
from common.redis_schema.markets import DeribitInstrumentType


def test_parse_deribit_spot_key():
    key = "markets:deribit:spot:btc:usd"
    descriptor = parse_deribit_market_key(key)

    assert descriptor.instrument_type is DeribitInstrumentType.SPOT
    assert descriptor.currency == "BTC"
    assert descriptor.quote_currency == "USD"
    assert descriptor.expiry_iso is None


def test_parse_deribit_future_key():
    key = "markets:deribit:future:eth:20240628"
    descriptor = parse_deribit_market_key(key)

    assert descriptor.instrument_type is DeribitInstrumentType.FUTURE
    assert descriptor.expiry_iso == "20240628"
    assert descriptor.currency == "ETH"


def test_parse_deribit_option_key():
    key = "markets:deribit:option:btc:20240119:25000:c"
    descriptor = parse_deribit_market_key(key)

    assert descriptor.instrument_type is DeribitInstrumentType.OPTION
    assert descriptor.strike == "25000"
    assert descriptor.option_kind == "c"
    assert descriptor.expiry_token == "20240119"


@pytest.mark.parametrize(
    "bad_key, message",
    [
        ("", "Key must be a non-empty string"),
        ("markets:other:spot:btc:usd", "Key is not within the Deribit markets namespace"),
        ("markets:deribit:unknown:btc", "Unsupported Deribit instrument type"),
        ("markets:deribit:spot:btc", "Spot key must include quote currency"),
        ("markets:deribit:future:btc", "Future key must include expiry segment"),
        ("markets:deribit:option:btc:20240119", "Option key must include expiry"),
    ],
)
def test_parse_deribit_key_validation_errors(bad_key, message):
    with pytest.raises(ValueError, match=message):
        parse_deribit_market_key(bad_key)


def test_parse_deribit_key_requires_normalized_form():
    malformed = "markets:deribit:spot:btc:Usd"  # incorrect casing should fail normalization check
    with pytest.raises(ValueError, match="does not match normalized form"):
        parse_deribit_market_key(malformed)
