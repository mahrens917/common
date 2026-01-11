import logging
from types import SimpleNamespace

import pytest

from common.redis_protocol.kalshi_store.reader_helpers import market_filter


class _DummyRedis:
    def __init__(self):
        self.calls = 0

    async def scan(self, cursor, match, count):
        if self.calls == 0:
            self.calls += 1
            return 0, [b"kalshi:btc:TK1"]
        return 0, []


@pytest.mark.asyncio
async def test_find_currency_market_tickers_filters_by_currency(monkeypatch):
    redis = _DummyRedis()
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.market_filter.parse_kalshi_market_key",
        lambda key: SimpleNamespace(ticker="KXBTC-TK1"),
    )
    filt = market_filter.MarketFilter(logger_instance=logging.getLogger("test"))
    markets = await filt.find_currency_market_tickers(
        redis,
        "BTC",
        lambda ticker, currency: ticker.startswith("KX"),
    )
    assert markets == ["KXBTC-TK1"]


def test_log_market_summary_skips_zero():
    filt = market_filter.MarketFilter(logger_instance=logging.getLogger("test"))
    filt.log_market_summary(currency="BTC", total=0, processed=0, skip_reasons={})


@pytest.mark.asyncio
async def test_find_all_market_tickers_returns_all_tickers(monkeypatch):
    redis = _DummyRedis()
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.market_filter.parse_kalshi_market_key",
        lambda key: SimpleNamespace(ticker="KXBTC-TK1"),
    )
    filt = market_filter.MarketFilter(logger_instance=logging.getLogger("test"))
    markets = await filt.find_all_market_tickers(redis)
    assert markets == ["KXBTC-TK1"]
