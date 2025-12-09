from collections import Counter
from types import SimpleNamespace

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers import market_lookup


@pytest.mark.asyncio
async def test_get_markets_by_currency_invokes_build(monkeypatch):
    async def fake_build(*args, **kwargs):
        return (["market"], Counter())

    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.market_lookup.build_market_records",
        fake_build,
    )

    class DummyFilter:
        async def find_currency_market_tickers(self, redis, currency, matcher):
            return ["TK1"]

        def log_market_summary(self, **kwargs):
            return None

    class DummyTickerParser:
        def is_market_for_currency(self, ticker, currency):
            return True

    lookup = market_lookup.MarketLookup("logger", "metadata", DummyFilter(), DummyTickerParser())
    setattr(market_lookup.MarketLookup, "log_market_summary", lambda self, **kwargs: None)
    result = await market_lookup.MarketLookup.get_markets_by_currency(
        lookup, "redis", "USD", DummyFilter(), lambda x: x
    )
    assert result == ["market"]


@pytest.mark.asyncio
async def test_get_market_data_for_strike_expiry_uses_strike_matcher(monkeypatch):
    async def fake_find(*args, **kwargs):
        return {"market_ticker": "TK"}

    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.market_lookup.find_matching_market",
        fake_find,
    )
    lookup = market_lookup.MarketLookup("logger", "metadata", SimpleNamespace(), SimpleNamespace())
    result = await market_lookup.MarketLookup.get_market_data_for_strike_expiry(
        lookup, "redis", "USD", "expiry", 1.0, [" markets"], lambda key: key
    )
    assert result == {"market_ticker": "TK"}
