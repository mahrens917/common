import math
from datetime import datetime, timezone

import pytest

from src.common.data_models.market_data import (
    DeribitFuturesData,
    DeribitOptionData,
    Instrument,
    MicroPriceOptionData,
)

_VAL_100_0 = 100.0
_VAL_101_0 = 101.0
DEFAULT_MICRO_PRICE_BID_SIZE = 2.0
DEFAULT_MICRO_PRICE_ASK_SIZE = 3.0


def _make_timestamp():
    return datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_deribit_futures_sets_missing_best_quotes():
    data = DeribitFuturesData(
        instrument_name="BTC-29DEC23",
        underlying="BTC",
        expiry_timestamp=1735430400,
        bid_price=100.0,
        ask_price=101.0,
        best_bid_size=5.0,
        best_ask_size=4.0,
        timestamp=_make_timestamp(),
    )

    assert data.best_bid == _VAL_100_0
    assert data.best_ask == _VAL_101_0


def test_deribit_futures_validation():
    with pytest.raises(ValueError):
        DeribitFuturesData(
            instrument_name="BTC-FAIL",
            underlying="BTC",
            expiry_timestamp=1735430400,
            bid_price=-1.0,
            ask_price=1.0,
            best_bid_size=1.0,
            best_ask_size=1.0,
            timestamp=_make_timestamp(),
        )


def test_deribit_option_validation():
    with pytest.raises(ValueError):
        DeribitOptionData(
            instrument_name="BTC-100-C",
            underlying="BTC",
            strike=0.0,
            expiry_timestamp=1735430400,
            option_type="call",
            bid_price=1.0,
            ask_price=1.2,
            best_bid_size=1.0,
            best_ask_size=1.0,
            timestamp=_make_timestamp(),
        )


def _make_micro_price_option() -> MicroPriceOptionData:
    best_bid = 100.0
    best_ask = 101.0
    bid_size = DEFAULT_MICRO_PRICE_BID_SIZE
    ask_size = DEFAULT_MICRO_PRICE_ASK_SIZE
    absolute_spread = best_ask - best_bid
    total_volume = bid_size + ask_size
    i_raw = bid_size / total_volume
    p_raw = (best_bid * ask_size + best_ask * bid_size) / total_volume
    relative_spread = absolute_spread / p_raw
    g = math.log(absolute_spread)
    h = math.log(i_raw / (1 - i_raw))

    return MicroPriceOptionData(
        instrument_name="OPT-TEST",
        underlying="BTC",
        strike=9500.0,
        expiry=_make_timestamp(),
        option_type="call",
        best_bid=best_bid,
        best_ask=best_ask,
        best_bid_size=bid_size,
        best_ask_size=ask_size,
        timestamp=_make_timestamp(),
        absolute_spread=absolute_spread,
        relative_spread=relative_spread,
        i_raw=i_raw,
        p_raw=p_raw,
        g=g,
        h=h,
        forward_price=9500.0,
        discount_factor=0.99,
    )


def test_micro_price_option_properties_and_validation():
    option = _make_micro_price_option()

    assert option.bid_price == option.best_bid
    assert option.ask_price == option.best_ask
    assert option.spread == option.absolute_spread
    assert option.p_raw > 0.0
    assert option.i_raw == pytest.approx(
        option.best_bid_size / (option.best_bid_size + option.best_ask_size)
    )
    assert option.is_future is False
    assert option.expiry_timestamp == int(option.expiry.timestamp())
    assert option.validate_micro_price_constraints() is True
    assert option.is_valid() is True

    intrinsic = option.intrinsic_value(spot_price=9600.0)
    assert intrinsic >= 0.0
    assert option.time_value(spot_price=9600.0) >= 0.0


def test_micro_price_option_invalid_relative_spread():
    option = _make_micro_price_option()
    with pytest.raises(ValueError):
        MicroPriceOptionData(
            instrument_name=option.instrument_name,
            underlying=option.underlying,
            strike=option.strike,
            expiry=option.expiry,
            option_type=option.option_type,
            best_bid=option.best_bid,
            best_ask=option.best_ask,
            best_bid_size=option.best_bid_size,
            best_ask_size=option.best_ask_size,
            timestamp=option.timestamp,
            absolute_spread=option.absolute_spread,
            relative_spread=option.relative_spread * 1.5,
            i_raw=option.i_raw,
            p_raw=option.p_raw,
            g=option.g,
            h=option.h,
            forward_price=option.forward_price,
            discount_factor=option.discount_factor,
        )


def test_micro_price_option_get_validation_errors_reports_issues():
    option = _make_micro_price_option()
    option.best_bid_size = -5.0
    errors = option.get_validation_errors()
    assert any("Bid size cannot be negative" in msg for msg in errors)
    option.i_raw = 1.5
    errors = option.get_validation_errors()
    assert any("Intensity constraint violated" in msg for msg in errors)
    assert option.is_valid() is False


def test_micro_price_option_from_enhanced_option_data():
    class EnhancedOption:
        instrument_name = "BTC-31DEC24-50000-C"
        underlying = ""
        strike = 50000.0
        expiry_timestamp = 1735603200
        option_type = "call"
        best_bid = 100.0
        best_ask = 101.0
        best_bid_size = DEFAULT_MICRO_PRICE_BID_SIZE
        best_ask_size = DEFAULT_MICRO_PRICE_ASK_SIZE
        timestamp = _make_timestamp()

    converted = MicroPriceOptionData.from_enhanced_option_data(EnhancedOption())
    assert converted.underlying == "BTC"
    assert converted.absolute_spread == pytest.approx(1.0)
    assert converted.p_raw == pytest.approx(100.4)
    assert converted.is_call is True
    assert converted.is_put is False


def test_micro_price_option_from_enhanced_option_data_requires_currency():
    class EnhancedOption:
        instrument_name = "UNKNOWN-31DEC"
        strike = 50000.0
        expiry_timestamp = 1735603200
        option_type = "call"
        best_bid = 100.0
        best_ask = 101.0
        best_bid_size = DEFAULT_MICRO_PRICE_BID_SIZE
        best_ask_size = DEFAULT_MICRO_PRICE_ASK_SIZE
        timestamp = _make_timestamp()

    with pytest.raises(ValueError):
        MicroPriceOptionData.from_enhanced_option_data(EnhancedOption())


def test_instrument_validation():
    instrument = Instrument(
        instrument_name="BTC-TEST",
        underlying="BTC",
        expiry_timestamp=1735603200,
        bid_price=100.0,
        ask_price=101.0,
        best_bid_size=1.0,
        best_ask_size=1.2,
        timestamp=_make_timestamp(),
    )
    assert instrument.bid_price == _VAL_100_0


def test_micro_price_option_forward_discount_validation():
    base = _make_micro_price_option()
    with pytest.raises(ValueError, match="Forward price must be positive"):
        MicroPriceOptionData(
            **{
                **base.__dict__,
                "forward_price": -1.0,
            }
        )
    with pytest.raises(ValueError, match="Discount factor must be positive"):
        MicroPriceOptionData(
            **{
                **base.__dict__,
                "discount_factor": 0.0,
            }
        )


def test_micro_price_option_intrinsic_and_time_values():
    option = _make_micro_price_option()
    call_intrinsic = option.intrinsic_value(spot_price=option.strike + 200)
    call_time = option.time_value(spot_price=option.strike + 200)
    assert call_intrinsic > 0
    assert call_time >= 0

    put_option = _make_micro_price_option()
    put_option.option_type = "put"
    put_intrinsic = put_option.intrinsic_value(spot_price=put_option.strike - 50)
    assert put_intrinsic > 0
    assert put_option.is_put is True

    with pytest.raises(ValueError):
        Instrument(
            instrument_name="BTC-FAIL",
            underlying="BTC",
            expiry_timestamp=1735603200,
            bid_price=10.0,
            ask_price=9.0,
        )
