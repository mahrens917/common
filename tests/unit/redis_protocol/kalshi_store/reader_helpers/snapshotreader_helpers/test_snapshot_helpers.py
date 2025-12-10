import pytest

from common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.field_accessor import (
    get_market_field,
)
from common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.market_tracker import (
    is_market_tracked,
)
from common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.metadata_operations import (
    get_market_metadata,
)
from common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.snapshot_retriever import (
    KalshiStoreError,
    get_market_snapshot,
)
from common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.subscription_retriever import (
    get_subscribed_markets,
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


@pytest.mark.asyncio
async def test_get_market_field_returns_value_and_handles_failure():
    redis = _SimpleRedis(value="present")
    assert await get_market_field(redis, "key", "ticker", "field") == "present"

    redis = _SimpleRedis(value=None)
    assert await get_market_field(redis, "key", "ticker", "field") == ""

    redis = _SimpleRedis(exc=RuntimeError("oops"))
    assert await get_market_field(redis, "key", "ticker", "field") == ""


@pytest.mark.asyncio
async def test_get_market_metadata_uses_adapter(monkeypatch):
    async def fake_snapshot(*_args, **_kwargs):
        return {"field": "value", "yes_bids": "keep", "no_asks": "keep"}

    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.snapshotreader_helpers.metadata_operations.get_market_snapshot",
        fake_snapshot,
    )

    class Adapter:
        def ensure_market_metadata_fields(self, _ticker, snapshot):
            return {**snapshot, "enriched": True}

    result = await get_market_metadata(None, "key", "TICK", None, Adapter())
    assert result["enriched"] is True
    assert "yes_bids" not in result


@pytest.mark.asyncio
async def test_get_market_snapshot_errors_and_filters(monkeypatch):
    extractor = _StubMetadataExtractor()
    redis = _SimpleRedis(exc=RuntimeError("fail"))
    with pytest.raises(KalshiStoreError):
        await get_market_snapshot(redis, "key", "TICK", extractor)

    redis = _SimpleRedis(value={})
    with pytest.raises(KalshiStoreError):
        await get_market_snapshot(redis, "key", "TICK", extractor)

    redis = _SimpleRedis(value={"yes_bids": "1", "market": "value"})
    snapshot = await get_market_snapshot(redis, "key", "TICK", extractor, include_orderbook=False)
    assert "yes_bids" not in snapshot
    assert extractor.synced

    with pytest.raises(TypeError):
        await get_market_snapshot(redis, "key", "", extractor)


@pytest.mark.asyncio
async def test_is_market_tracked_and_subscription_retriever():
    redis = _SimpleRedis(value=True)
    assert await is_market_tracked(redis, "key", "TICK")

    redis = _SimpleRedis(exc=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await is_market_tracked(redis, "key", "TICK")

    redis = _SimpleRedis(value={b"svc:XYZ": "1", "bad": "1"})
    markets = await get_subscribed_markets(redis, "subs")
    assert markets == {"XYZ"}

    redis = _SimpleRedis(exc=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await get_subscribed_markets(redis, "subs")
