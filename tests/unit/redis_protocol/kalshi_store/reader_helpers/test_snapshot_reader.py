import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.snapshot_reader import SnapshotReader


class _StubMetadataExtractor:
    def normalize_hash(self, raw):
        return dict(raw)

    def sync_top_of_book_fields(self, snapshot):
        pass


class _StubMetadataAdapter:
    def ensure_market_metadata_fields(self, ticker, snapshot):
        return {"metadata": ticker}


def _make_reader():
    return SnapshotReader(
        logger_instance=logging.getLogger(__name__),
        metadata_extractor=_StubMetadataExtractor(),
        metadata_adapter=_StubMetadataAdapter(),
    )


@pytest.mark.asyncio
async def test_snapshot_reader_methods():
    reader = _make_reader()

    # get_subscribed_markets
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={b"svc:markets": "1"})
    result = await reader.get_subscribed_markets(redis, "key")
    assert result == {"markets"}

    # is_market_tracked
    redis.exists = AsyncMock(return_value=1)
    assert await reader.is_market_tracked(redis, "key", "TK")

    # get_market_snapshot
    redis.hgetall = AsyncMock(return_value={b"data": b"value"})
    snapshot = await reader.get_market_snapshot(redis, "key", "TK")
    assert b"data" in snapshot

    # get_market_metadata
    redis.hgetall = AsyncMock(return_value={b"field": b"val"})
    metadata = await reader.get_market_metadata(redis, "key", "TK")
    assert metadata["metadata"] == "TK"

    # get_market_field
    redis.hget = AsyncMock(return_value="field_value")
    field = await reader.get_market_field(redis, "key", "TK", "field")
    assert field == "field_value"
