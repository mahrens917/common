import pytest

from common.redis_protocol.kalshi_store.reader_helpers import snapshot_reader


@pytest.mark.asyncio
async def test_snapshot_reader_methods(monkeypatch):
    async def _get_subscribed(*_args, **_kwargs):
        return {"markets"}

    async def _is_tracked(*_args, **_kwargs):
        return True

    async def _get_snapshot(_redis, _key, ticker, *_args, **_kwargs):
        return {"snapshot": ticker}

    async def _get_metadata(_redis, _key, ticker, *_args, **_kwargs):
        return {"metadata": ticker}

    async def _get_field(_redis, _key, _ticker, field):
        return field

    monkeypatch.setattr(snapshot_reader, "get_subscribed_markets", _get_subscribed)
    monkeypatch.setattr(snapshot_reader, "is_market_tracked", _is_tracked)
    monkeypatch.setattr(snapshot_reader, "get_market_snapshot", _get_snapshot)
    monkeypatch.setattr(snapshot_reader, "get_market_metadata", _get_metadata)
    monkeypatch.setattr(snapshot_reader, "get_market_field", _get_field)

    reader = snapshot_reader.SnapshotReader(logger_instance=None, metadata_extractor="extractor", metadata_adapter="adapter")
    assert await reader.get_subscribed_markets("redis", "key") == {"markets"}
    assert await reader.is_market_tracked("redis", "key", "TK") is True
    snapshot = await reader.get_market_snapshot("redis", "key", "TK")
    metadata = await reader.get_market_metadata("redis", "key", "TK")
    field = await reader.get_market_field("redis", "key", "TK", "field")
    assert snapshot["snapshot"] == "TK"
    assert metadata["metadata"] == "TK"
    assert field == "field"
