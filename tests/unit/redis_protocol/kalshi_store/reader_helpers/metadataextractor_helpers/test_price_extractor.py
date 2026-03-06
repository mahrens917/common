"""Tests for the price extractor helper."""

from common.redis_protocol.kalshi_store.reader_helpers.metadataextractor_helpers.utilities import (
    extract_market_prices,
)


def test_extract_market_prices_returns_floats():
    bid, ask = extract_market_prices({"yes_bid": "1.5", "yes_ask": 2})
    assert bid == 1.5
    assert ask == 2.0


def test_extract_market_prices_handles_missing():
    bid, ask = extract_market_prices({"yes_bid": None, "yes_ask": ""})
    assert bid is None
    assert ask is None


def test_extract_market_prices_handles_invalid_values():
    bid, ask = extract_market_prices({"yes_bid": "bad", "yes_ask": object()})
    assert bid is None
    assert ask is None
