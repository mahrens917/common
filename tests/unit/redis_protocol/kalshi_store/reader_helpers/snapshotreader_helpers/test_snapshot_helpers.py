import logging

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader import (
    KalshiStoreError,
    SnapshotReader,
)


class _SimpleRedis:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    async def hget(self, *_args, **_kwargs):
        if self.exc:
            raise self.exc
        return self.value

    async def hgetall(self, *_args, **_kwargs):
        if self.exc:
            raise self.exc
        return self.value

    async def exists(self, *_args, **_kwargs):
        if self.exc:
            raise self.exc
        return self.value


class _StubMetadataExtractor:
    def __init__(self):
        self.normalized = None
        self.synced = False

    def normalize_hash(self, raw):
        self.normalized = dict(raw)
        return self.normalized

    def sync_top_of_book_fields(self, snapshot):
        self.synced = True
        snapshot["yes_bid"] = snapshot.get("yes_bid", "synced")


class _StubMetadataAdapter:
    def ensure_market_metadata_fields(self, ticker, snapshot):
        return {**snapshot, "enriched": True}


def _make_reader(extractor=None, adapter=None):
    return SnapshotReader(
        logger_instance=logging.getLogger(__name__),
        metadata_extractor=extractor or _StubMetadataExtractor(),
        metadata_adapter=adapter or _StubMetadataAdapter(),
    )


@pytest.mark.asyncio
async def test_get_market_field_returns_value_and_handles_failure():
    reader = _make_reader()
    redis = _SimpleRedis(value="present")
    assert await reader.get_market_field(redis, "key", "ticker", "field") == "present"

    redis = _SimpleRedis(value=None)
    assert await reader.get_market_field(redis, "key", "ticker", "field") == ""

    redis = _SimpleRedis(exc=RuntimeError("oops"))
    assert await reader.get_market_field(redis, "key", "ticker", "field") == ""


@pytest.mark.asyncio
async def test_get_market_metadata_uses_adapter():
    extractor = _StubMetadataExtractor()
    adapter = _StubMetadataAdapter()
    reader = _make_reader(extractor, adapter)

    redis = _SimpleRedis(value={"field": "value", "yes_bids": "keep", "no_asks": "keep"})
    result = await reader.get_market_metadata(redis, "key", "TICK")
    assert result["enriched"] is True
    assert "yes_bids" not in result


@pytest.mark.asyncio
async def test_get_market_snapshot_errors_and_filters():
    extractor = _StubMetadataExtractor()
    reader = _make_reader(extractor)
    redis = _SimpleRedis(exc=RuntimeError("fail"))
    with pytest.raises(KalshiStoreError):
        await reader.get_market_snapshot(redis, "key", "TICK")

    redis = _SimpleRedis(value={})
    with pytest.raises(KalshiStoreError):
        await reader.get_market_snapshot(redis, "key", "TICK")

    redis = _SimpleRedis(value={"yes_bids": "1", "market": "value"})
    snapshot = await reader.get_market_snapshot(redis, "key", "TICK", include_orderbook=False)
    assert "yes_bids" not in snapshot
    assert extractor.synced

    with pytest.raises(TypeError):
        await reader.get_market_snapshot(redis, "key", "")


@pytest.mark.asyncio
async def test_is_market_tracked_and_subscription_retriever():
    reader = _make_reader()
    redis = _SimpleRedis(value=True)
    assert await reader.is_market_tracked(redis, "key", "TICK")

    redis = _SimpleRedis(exc=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await reader.is_market_tracked(redis, "key", "TICK")

    redis = _SimpleRedis(value={b"svc:XYZ": "1", "bad": "1"})
    markets = await reader.get_subscribed_markets(redis, "subs")
    assert markets == {"XYZ"}

    redis = _SimpleRedis(exc=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await reader.get_subscribed_markets(redis, "subs")
