"""Unit tests for the Kalshi strike type extractor."""

import pytest

from common.market_data.strike_type import extract_strike_type_from_ticker


@pytest.mark.parametrize(
    "ticker,expected",
    [
        ("KXBTC-ABOVE-10", "greater"),
        ("kxbtc-below-10", "less"),
        ("KXBTC-BETWEEN-10-20", "between"),
        ("PRICE>50", "greater"),
        ("PRICE<40", "less"),
    ],
)
def test_extract_strike_type_from_ticker_recognizes_patterns(ticker, expected):
    assert extract_strike_type_from_ticker(ticker) == expected


def test_extract_strike_type_structural_between():
    assert extract_strike_type_from_ticker("ABC-DEF-GHI") == "between"


def test_extract_strike_type_returns_none_when_not_recognized_and_not_forced():
    assert extract_strike_type_from_ticker("UNKNOWN", raise_on_failure=False) is None


def test_extract_strike_type_raises_when_not_recognized():
    with pytest.raises(RuntimeError, match="Unable to determine strike_type"):
        extract_strike_type_from_ticker("UNKNOWN")
