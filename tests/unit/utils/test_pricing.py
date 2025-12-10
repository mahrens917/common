import math

import pytest

from common.utils import pricing


def test_calculate_usdc_micro_price_volume_weighted():
    result = pricing.calculate_usdc_micro_price(100.0, 102.0, 10.0, 5.0)
    expected = (100.0 * 5.0 + 102.0 * 10.0) / 15.0
    assert math.isclose(result, expected)


def test_calculate_usdc_micro_price_zero_total_size_errors():
    with pytest.raises(ValueError) as excinfo:
        pricing.calculate_usdc_micro_price(100.0, 101.0, 0.0, 0.0)
    assert "Total order book size" in str(excinfo.value)


@pytest.mark.parametrize(
    "bid_price, ask_price, bid_size, ask_size, message",
    [
        (0.0, 101.0, 1.0, 1.0, "Invalid bid price"),
        (100.0, 0.0, 1.0, 1.0, "Invalid ask price"),
        (102.0, 101.0, 1.0, 1.0, "Invalid spread"),
        (100.0, 101.0, -1.0, 1.0, "Invalid bid size"),
        (100.0, 101.0, 1.0, -1.0, "Invalid ask size"),
    ],
)
def test_calculate_usdc_micro_price_validation_errors(
    bid_price, ask_price, bid_size, ask_size, message
):
    with pytest.raises(ValueError) as excinfo:
        pricing.calculate_usdc_micro_price(bid_price, ask_price, bid_size, ask_size)
    assert message in str(excinfo.value)


def test_validate_usdc_bid_ask_prices_returns_validated_values():
    assert pricing.validate_usdc_bid_ask_prices(100.0, 101.0) == (100.0, 101.0)


@pytest.mark.parametrize(
    "bid_price, ask_price, message",
    [
        (0.0, 101.0, "Invalid bid price"),
        (100.0, 0.0, "Invalid ask price"),
        (102.0, 101.0, "Invalid spread"),
    ],
)
def test_validate_usdc_bid_ask_prices_errors(bid_price, ask_price, message):
    with pytest.raises(ValueError) as excinfo:
        pricing.validate_usdc_bid_ask_prices(bid_price, ask_price)
    assert message in str(excinfo.value)


def test_calculate_price_change_percentage():
    assert pricing.calculate_price_change_percentage(100.0, 110.0) == pytest.approx(10.0)


@pytest.mark.parametrize(
    "old_price, new_price, message",
    [
        (0.0, 1.0, "Invalid old price"),
        (1.0, 0.0, "Invalid new price"),
    ],
)
def test_calculate_price_change_percentage_validations(old_price, new_price, message):
    with pytest.raises(ValueError) as excinfo:
        pricing.calculate_price_change_percentage(old_price, new_price)
    assert message in str(excinfo.value)


def test_calculate_strike_moneyness_ratio():
    assert pricing.calculate_strike_moneyness_ratio(105.0, 100.0) == pytest.approx(1.05)


@pytest.mark.parametrize(
    "strike, spot, message",
    [
        (0.0, 100.0, "Invalid strike price"),
        (100.0, 0.0, "Invalid spot price"),
    ],
)
def test_calculate_strike_moneyness_ratio_validations(strike, spot, message):
    with pytest.raises(ValueError) as excinfo:
        pricing.calculate_strike_moneyness_ratio(strike, spot)
    assert message in str(excinfo.value)
