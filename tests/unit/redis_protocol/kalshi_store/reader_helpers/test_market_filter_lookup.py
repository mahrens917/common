import logging
from collections import Counter
from types import SimpleNamespace

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.market_filter import MarketFilter
from common.redis_protocol.kalshi_store.reader_helpers.market_lookup import MarketLookup


class _ScanRedis:
    def __init__(self, batches):
        self.batches = batches
        self.index = 0

    async def scan(self, cursor, match=None, count=None):
        batch = self.batches[self.index]
        self.index = min(self.index + 1, len(self.batches) - 1)
        return batch


@pytest.mark.asyncio
async def test_market_filter_scan_and_summary(monkeypatch, caplog):
    # Build redis scan output: continue once then stop
    redis = _ScanRedis(
        [
            (1, [b"kalshi:good", "kalshi:dup", "invalid"]),
            (0, ["kalshi:good", "kalshi:other"]),
        ]
    )
    captured = []

    def fake_parse(key):
        if "invalid" in key:
            raise ValueError("bad key")
        return SimpleNamespace(ticker=key.split(":")[-1])

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.market_filter.parse_kalshi_market_key",
        fake_parse,
    )

    filt = MarketFilter(logging.getLogger("test_market_filter"))
    is_for_currency = lambda ticker, currency: ticker != "other" and currency == "usd"

    tickers = await filt.find_currency_market_tickers(redis, "usd", is_for_currency)
    assert tickers == ["good", "dup"]

    # Summary logs only when total > 0
    with caplog.at_level("DEBUG"):
        filt.log_market_summary(
            currency="usd",
            total=2,
            processed=1,
            skip_reasons=Counter({"expired": 1, "other": 3}),
        )
    assert "Processed 1/2 active markets for usd" in caplog.text
    assert "expired=1" in caplog.text
    caplog.clear()
    filt.log_market_summary(currency="usd", total=0, processed=0, skip_reasons=Counter())
    assert caplog.text == ""


@pytest.mark.asyncio
async def test_market_lookup_branches(monkeypatch):
    logger = logging.getLogger("test_market_lookup")
    metadata_extractor = SimpleNamespace()
    orderbook_reader = SimpleNamespace()
    ticker_parser = SimpleNamespace(is_market_for_currency=lambda ticker, _ccy: True)
    lookup = MarketLookup(logger, metadata_extractor, orderbook_reader, ticker_parser)

    # No tickers path
    class _EmptyFilter:
        async def find_currency_market_tickers(self, redis, currency, fn):
            return []

        def log_market_summary(self, **kwargs):
            raise AssertionError("should not log when no tickers")

    redis = SimpleNamespace()
    result = await lookup.get_markets_by_currency(redis, "usd", _EmptyFilter(), lambda t: t)
    assert result == []

    # Successful path
    summary_calls = []

    class _Filter:
        async def find_currency_market_tickers(self, redis, currency, fn):
            return ["AAA", "BBB"]

        def log_market_summary(self, **kwargs):
            summary_calls.append(kwargs)

    async def fake_build_market_records(**kwargs):
        return ([{"ticker": "AAA"}], Counter({"expired": 1}))

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.market_lookup.build_market_records",
        fake_build_market_records,
    )

    result = await lookup.get_markets_by_currency(redis, "usd", _Filter(), lambda t: f"k:{t}")
    assert result == [{"ticker": "AAA"}]
    assert summary_calls and summary_calls[0]["total"] == 2

    # Strike/expiry path delegates to find_matching_market
    observed_deps = {}

    async def fake_find_matching_market(deps):
        observed_deps["strike"] = deps.strike
        observed_deps["expiry"] = deps.expiry
        observed_deps["markets"] = deps.markets
        return {"match": deps.strike}

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.market_lookup.find_matching_market",
        fake_find_matching_market,
    )

    match = await lookup.get_market_data_for_strike_expiry(
        redis, "usd", "2024-01-01", 12.5, ["m1"], lambda ticker: f"key:{ticker}"
    )
    assert match == {"match": 12.5}
    assert observed_deps["markets"] == ["m1"]
