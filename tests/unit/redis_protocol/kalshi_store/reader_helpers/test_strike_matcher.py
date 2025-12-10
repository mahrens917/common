from types import SimpleNamespace

import pytest

from common.redis_protocol.kalshi_store.reader_helpers import strike_matcher


class _DummyTickerParser:
    def iter_currency_markets(self, markets, currency):
        return ["TK1"]


class _DummyMetadataExtractor:
    def parse_market_metadata(self, ticker, data):
        return {"close_time": "2025-01-01", "strike": 1.0}

    def resolve_market_strike(self, metadata):
        return metadata["strike"]

    def extract_market_prices(self, metadata):
        return 1.0, 2.0


class _DummyOrderbookReader:
    def extract_orderbook_sizes(self, ticker, data):
        return 1.0, 2.0


class _DummyRedis:
    async def hgetall(self, key):
        return {"close_time": "2025-01-01", "orderbook": '{"yes_bids":{"1":1},"yes_asks":{"2":2}}'}


@pytest.mark.asyncio
async def test_find_matching_market_success(monkeypatch):
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.strike_matcher.ensure_awaitable",
        lambda value: value,
    )
    deps = strike_matcher.MarketMatcherDependencies(
        redis=_DummyRedis(),
        currency="BTC",
        expiry="2025-01-01",
        strike=1.0,
        markets=["TK1"],
        get_market_key_func=lambda ticker: ticker,
        ticker_parser=_DummyTickerParser(),
        metadata_extractor=_DummyMetadataExtractor(),
        orderbook_reader=_DummyOrderbookReader(),
    )
    result = await strike_matcher.find_matching_market(deps)
    assert result is not None


def test_matches_strike_expiry_checks_bounds():
    assert strike_matcher._matches_strike_expiry(1.0, "2025-01-01", 1.0, "2025-01-01")
    assert not strike_matcher._matches_strike_expiry(None, "2025-01-01", 1.0, "2025-01-01")
