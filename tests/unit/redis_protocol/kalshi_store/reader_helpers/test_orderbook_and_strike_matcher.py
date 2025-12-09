import pytest

from src.common.exceptions import DataError
from src.common.redis_protocol.kalshi_store.reader_helpers.orderbook_parser import (
    extract_best_prices_from_orderbook,
    extract_orderbook_sizes,
    parse_orderbook_json,
    resolve_orderbook_size,
)
from src.common.redis_protocol.kalshi_store.reader_helpers.strike_matcher import (
    MarketMatcherDependencies,
    _matches_strike_expiry,
    find_matching_market,
)

BEST_BID_SIZE_FOR_MATCHER = 1.0
BEST_BID_SIZE_IN_PARSER = 2.0
BEST_ASK_SIZE_IN_PARSER = 3.0


class _FakeRedis:
    def __init__(self, payload):
        self.payload = payload

    async def hgetall(self, key):
        return self.payload


class _FakeMetadataExtractor:
    def __init__(self, metadata=None, strike=10.0):
        self.metadata = metadata or {}
        self.strike = strike

    def parse_market_metadata(self, market_ticker, market_data):
        return dict(self.metadata)

    def resolve_market_strike(self, metadata):
        return self.strike

    def extract_market_prices(self, metadata):
        return (0.1, 0.2)


class _FakeOrderbookReader:
    def __init__(self, sizes=(1.0, 2.0)):
        self.sizes = sizes

    def extract_orderbook_sizes(self, market_ticker, market_data):
        return self.sizes


class _TickerParser:
    def __init__(self, tickers):
        self._tickers = tickers

    def iter_currency_markets(self, markets, currency):
        return list(self._tickers)


@pytest.mark.asyncio
async def test_find_matching_market_and_strike_matcher():
    deps = MarketMatcherDependencies(
        redis=_FakeRedis({"orderbook": b'{"yes_bids":{"0.1": 1},"yes_asks":{"0.2": 2}}'}),
        currency="usd",
        expiry="2024-01-01",
        strike=10.0,
        markets=["m1"],
        get_market_key_func=lambda ticker: f"key:{ticker}",
        ticker_parser=_TickerParser(["m1", "m2"]),
        metadata_extractor=_FakeMetadataExtractor({"close_time": "2024-01-01"}),
        orderbook_reader=_FakeOrderbookReader(),
    )

    result = await find_matching_market(deps)
    assert result["market_ticker"] == "m1"
    assert result["best_bid_size"] == BEST_BID_SIZE_FOR_MATCHER

    # Mismatched strike/expiry combinations return None
    assert _matches_strike_expiry(10.0, "2024-01-01", 10.0, "2024-01-01") is True
    assert _matches_strike_expiry(None, "2024", 10.0, "2024") is False
    assert _matches_strike_expiry(10.0, "wrong", 10.0, "2024") is False
    assert _matches_strike_expiry(10.5, "2024", 10.0, "2024") is False

    bad_deps = MarketMatcherDependencies(
        redis=_FakeRedis({}),
        currency="usd",
        expiry="2024-01-01",
        strike=10.0,
        markets=["m1"],
        get_market_key_func=lambda ticker: f"key:{ticker}",
        ticker_parser=_TickerParser(["m1"]),
        metadata_extractor=_FakeMetadataExtractor({"close_time": None}),
        orderbook_reader=_FakeOrderbookReader(),
    )
    assert await find_matching_market(bad_deps) is None


def test_orderbook_parser_happy_paths_and_errors():
    market_data = {"orderbook": b'{"yes_bids":{"0.1": 2},"yes_asks":{"0.1": 3}}'}
    best_bid_size, best_ask_size = extract_orderbook_sizes("TCKR", market_data)
    assert best_bid_size == BEST_BID_SIZE_IN_PARSER
    assert best_ask_size == BEST_ASK_SIZE_IN_PARSER

    # parse_orderbook_json handles bytes and empty input
    assert parse_orderbook_json(None, "orderbook", "TCKR") == {}
    parsed = parse_orderbook_json(b'{"a":1}', "orderbook", "TCKR")
    assert parsed == {"a": 1}

    # resolve_orderbook_size falls back to general formatting
    assert resolve_orderbook_size({"0.2": "5"}, 0.2, "TCKR") == 5.0
    with pytest.raises(RuntimeError):
        resolve_orderbook_size({}, 0.3, "TCKR")

    # Error branches
    with pytest.raises(DataError):
        extract_orderbook_sizes("TCKR", {})
    with pytest.raises(TypeError):
        extract_orderbook_sizes("TCKR", {"orderbook": b"[]"})
    with pytest.raises(DataError):
        extract_orderbook_sizes("TCKR", {"orderbook": b'{"yes_bids":{},"yes_asks":{}}'})

    with pytest.raises(DataError):
        extract_best_prices_from_orderbook({"yes_bids": {}, "yes_asks": {}}, "TCKR")
    bid, ask = extract_best_prices_from_orderbook(
        {"yes_bids": {"0.1": 1}, "yes_asks": {"0.2": 1}}, "TCKR"
    )
    assert bid == 0.1 and ask == 0.2
