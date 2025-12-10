import pytest

from common.redis_protocol.kalshi_store.reader_helpers import snapshot_reader


class _DummyHelpers:
    async def get_subscribed_markets(self, redis, key):
        return {"markets"}

    async def is_market_tracked(self, redis, key, ticker):
        return True

    async def get_market_snapshot(self, redis, key, ticker, extractor, include_orderbook=True):
        return {"snapshot": ticker}

    async def get_market_metadata(self, redis, key, ticker, extractor, adapter):
        return {"metadata": ticker}

    async def get_market_field(self, redis, key, ticker, field):
        return field


@pytest.mark.asyncio
async def test_snapshot_reader_methods(monkeypatch):
    monkeypatch.setattr(
        "common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader.helpers",
        _DummyHelpers(),
    )
    reader = snapshot_reader.SnapshotReader(
        logger_instance=None, metadata_extractor="extractor", metadata_adapter="adapter"
    )
    assert await reader.get_subscribed_markets("redis", "key") == {"markets"}
    assert await reader.is_market_tracked("redis", "key", "TK") is True
    snapshot = await reader.get_market_snapshot("redis", "key", "TK")
    metadata = await reader.get_market_metadata("redis", "key", "TK")
    field = await reader.get_market_field("redis", "key", "TK", "field")
    assert snapshot["snapshot"] == "TK"
    assert metadata["metadata"] == "TK"
    assert field == "field"
