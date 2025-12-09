import pytest

from src.common.parsing_utils import decode_redis_key
from src.common.redis_protocol.kalshi_store.store_helpers.scanner import (
    add_unique_keys,
    scan_market_keys,
    scan_single_pattern,
)
from src.common.redis_protocol.kalshi_store.store_helpers.ticker_finder import (
    find_currency_market_tickers,
)


class _StoreWithReader:
    def __init__(self, keys):
        self._reader = self
        self._keys = keys
        self._calls = 0

    async def _scan_market_keys(self, patterns):
        self._calls += 1
        return self._keys


class _FakeRedis:
    def __init__(self, scans):
        self.scans = scans
        self.index = 0

    async def scan(self, cursor, match=None, count=None):
        current = self.scans[self.index]
        self.index = min(self.index + 1, len(self.scans) - 1)
        return current


class _Store:
    def __init__(self, redis=None, reader=None, ensure=True):
        self._reader = reader
        self._redis = redis
        self._ensure = ensure

    async def _ensure_redis_connection(self):
        return self._ensure

    async def _get_redis(self):
        return self._redis


def test_decode_and_add_unique_keys():
    results = []
    seen = set()
    add_unique_keys([b"one", "two", "one"], seen, results)
    assert results == ["one", "two"]
    assert decode_redis_key(b"bytes") == "bytes"
    assert decode_redis_key("str") == "str"


@pytest.mark.asyncio
async def test_scan_market_keys_prefers_reader(monkeypatch):
    store = _StoreWithReader(["k1", "k2"])
    assert await scan_market_keys(store) == ["k1", "k2"]
    assert store._calls == 1

    # Fallback path uses direct scan
    redis = _FakeRedis(scans=[(1, [b"a"]), (0, ["b", b"a"])])
    store = _Store(redis=redis, reader=None, ensure=True)
    keys = await scan_market_keys(store, patterns=["pattern:*"])
    assert keys == ["a", "b"]

    store = _Store(redis=redis, reader=None, ensure=False)
    with pytest.raises(RuntimeError):
        await scan_market_keys(store)


@pytest.mark.asyncio
async def test_scan_single_pattern_handles_cursor():
    redis = _FakeRedis(scans=[(1, [b"a"]), (0, [b"b"])])
    seen, results = set(), []
    await scan_single_pattern(redis, "pat:*", seen, results)
    assert results == ["a", "b"]


@pytest.mark.asyncio
async def test_ticker_finder_depends_on_reader():
    class _Reader:
        def __init__(self):
            self._market_filter = self
            self._ticker_parser = self
            self.calls = 0

        def is_market_for_currency(self, ticker, currency):
            return currency in ticker

        async def find_currency_market_tickers(self, redis, currency, fn):
            self.calls += 1
            return ["match"] if fn(f"{currency}-ticker", currency) else []

    class _StoreWithReaderOnly:
        def __init__(self, reader):
            self._reader = reader

        async def _get_redis(self):
            return object()

    reader = _Reader()
    store = _StoreWithReaderOnly(reader)
    tickers = await find_currency_market_tickers(store, "usd")
    assert tickers == ["match"]
    assert reader.calls == 1

    store_missing_reader = _Store(reader=None, redis=None)
    with pytest.raises(RuntimeError):
        await find_currency_market_tickers(store_missing_reader, "usd")

    class _ReaderMissingDeps:
        def __init__(self):
            self._market_filter = None
            self._ticker_parser = None

    with pytest.raises(RuntimeError):
        await find_currency_market_tickers(_StoreWithReaderOnly(_ReaderMissingDeps()), "usd")
